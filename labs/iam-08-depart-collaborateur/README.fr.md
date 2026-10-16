# Tutoriel : trois silences, vus sur votre propre situation

Ce tutoriel ne fait pas le challenge. Il vous montre les trois choses qui
échouent sans le dire, sur le compte qui part, avant que vous ne touchiez à
quoi que ce soit.

On lit d'abord. Chacun de ces trois a coûté à quelqu'un une vraie remarque
d'audit.

```bash
KC=http://127.0.0.1:8080
IDS=/opt/iam-lab/identifiants-lab.txt
QUI=$(grep '^QUI_PART=' $IDS | cut -d= -f2-)
U=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME=' /opt/socle-iam/.env | cut -d= -f2-)
P=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD=' /opt/socle-iam/.env | cut -d= -f2-)
ADM=$(curl -s -X POST "$KC/realms/master/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  -d "username=$U" -d "password=$P" | jq -r .access_token)
ID=$(curl -s "$KC/admin/realms/formation/users?username=$QUI&exact=true" \
  -H "Authorization: Bearer $ADM" | jq -r '.[0].id')
echo "$QUI : $ID"
```

Regardez ce qu'elle a, en un seul endroit :

```bash
echo "actif  : $(curl -s "$KC/admin/realms/formation/users/$ID" \
  -H "Authorization: Bearer $ADM" | jq -r .enabled)"
echo "groupes: $(curl -s "$KC/admin/realms/formation/users/$ID/groups" \
  -H "Authorization: Bearer $ADM" | jq -c '[.[].name]')"
echo "roles  : $(curl -s "$KC/admin/realms/formation/users/$ID/role-mappings" \
  -H "Authorization: Bearer $ADM" \
  | jq -c '[.realmMappings[]?.name] | map(select(startswith("default-roles-") | not))')"
echo "session: $(curl -s "$KC/admin/realms/formation/users/$ID/sessions" \
  -H "Authorization: Bearer $ADM" | jq length)"
```

Un rôle de cette liste appartient directement à son compte, et non à un groupe.
Retenez-le : une revue bâtie sur les appartenances aux groupes ne le montrera
jamais.

## Silence 1 : la session survit à la désactivation

Désactivez-la, exprès, pour voir ce que cela fait et ce que cela ne fait pas :

```bash
curl -s -o /dev/null -w 'desactivation : HTTP %{http_code}\n' -X PUT \
  "$KC/admin/realms/formation/users/$ID" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d '{"enabled":false}'

echo "actif   : $(curl -s "$KC/admin/realms/formation/users/$ID" \
  -H "Authorization: Bearer $ADM" | jq -r .enabled)"
echo "sessions: $(curl -s "$KC/admin/realms/formation/users/$ID/sessions" \
  -H "Authorization: Bearer $ADM" | jq length)"
```

Désactivée, et la session est toujours là. La fiche du compte dit ce que vous
voulez lire, et rien ne dit que la session continue.

Qu'est-ce que cette session permet encore ? Essayez le jeton de
rafraîchissement que le setup a laissé :

```bash
RT=$(grep '^REFRESH_TOKEN=' /opt/iam-lab/jetons-de-la-session.txt | cut -d= -f2-)
curl -s -X POST "$KC/realms/formation/protocol/openid-connect/token" \
  -d grant_type=refresh_token -d client_id=appli-notes \
  -d "refresh_token=$RT" | jq -c '{error, error_description}'
```

Refusé, avec une raison. La désactivation mord donc sur le rafraîchissement.
Mais regardez l'**access token**, qui est une tout autre chose :

```bash
AT=$(grep '^ACCESS_TOKEN=' /opt/iam-lab/jetons-de-la-session.txt | cut -d= -f2-)
echo "userinfo : $(curl -s -o /dev/null -w '%{http_code}' \
  "$KC/realms/formation/protocol/openid-connect/userinfo" \
  -H "Authorization: Bearer $AT")"

charge() {
  local c=$(echo "$1" | cut -d. -f2)
  local pad=$(( (4 - ${#c} % 4) % 4 ))
  [ "$pad" -gt 0 ] && c="$c$(printf '=%.0s' $(seq 1 "$pad"))"
  echo "$c" | tr '_-' '/+' | base64 -d
}
EXP=$(charge "$AT" | jq -r .exp)
echo "ce jeton expire dans $(( EXP - $(date +%s) )) secondes"
```

`userinfo` le refuse, parce que `userinfo` interroge Keycloak. Et le jeton
lui-même est toujours parfaitement signé et pas encore expiré.

Cette différence est tout le propos. Une API qui valide un jeton **hors ligne**,
avec la signature et les revendications, comme celle du lab 05, n'a aucune idée
que cette personne est partie. Elle acceptera ce jeton jusqu'à son `exp`. Rien
de ce que vous ferez dans ce lab ne raccourcit cette fenêtre : seule la durée de
vie des jetons le fait.

## Silence 2 : le fournisseur refuse, et il a raison

Essayez de retirer son groupe depuis le fournisseur :

```bash
GID=$(curl -s "$KC/admin/realms/formation/users/$ID/groups" \
  -H "Authorization: Bearer $ADM" | jq -r '.[0].id')
curl -s -X DELETE "$KC/admin/realms/formation/users/$ID/groups/$GID" \
  -H "Authorization: Bearer $ADM" | jq -r '.error // "(pas de corps)"'
```

Lisez le message. Ce n'est ni un défaut ni un problème de droits : le mappeur de
groupes est en lecture seule, donc l'annuaire possède cette appartenance et le
fournisseur refuse de le contredire. C'est exactement ce que le lab 3 a mis en
place, et c'est ce que vous voulez.

Le retrait se fait donc dans l'annuaire, par son API :

```bash
WEB=http://127.0.0.1:17170
MDP=$(grep '^LLDAP_ADMIN_PASSWORD=' /opt/socle-iam/.env | cut -d= -f2-)
JL=$(curl -s -X POST "$WEB/auth/simple/login" \
  -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg m "$MDP" '{username:"admin", password:$m}')" | jq -r .token)
curl -s -X POST "$WEB/api/graphql" -H "Authorization: Bearer $JL" \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ groups { id displayName } }"}' | jq -c '.data.groups'
```

Un avertissement avant de vous servir de cette API, et c'est le troisième
silence déguisé : elle répond HTTP `200` **avec** un tableau `errors` quand elle
refuse. Ne regarder que le code de statut fait passer un refus pour un succès.
Et son `groupId` est un **entier** : passez-le en chaîne et vous obtiendrez
exactement ce refus poli.

## Silence 3 : le fournisseur se souvient

Celui-là, vous le rencontrerez en dépannant, alors rencontrez-le ici.

Après avoir retiré une appartenance à la source, le fournisseur montre toujours
l'ancienne, même après avoir synchronisé le mappeur. La synchronisation annonce
des groupes mis à jour, et le compte garde son groupe.

Le fournisseur garde une vue en cache des comptes fédérés, et une
synchronisation de mappeur ne l'invalide pas. Il existe un point d'accès pour
cela, et le chercher fait partie du travail.

Remettez-la comme elle était, pour partir de la vraie situation :

```bash
curl -s -o /dev/null -w 'reactivation : HTTP %{http_code}\n' -X PUT \
  "$KC/admin/realms/formation/users/$ID" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d '{"enabled":true}'
```

La session que vous avez vue est toujours ouverte, et c'est bien : le challenge
l'attend.

## Une quatrième chose, sur la revue

La revue n'est pas de la paperasse. C'est la seule réponse à la seule question
qu'un audit pose : à quoi cette personne avait-elle accès, le jour de son
départ ?

Bâtissez-la depuis le fournisseur, pour chaque compte, avec les **groupes et
les rôles**. Les rôles sont la partie que les gens sautent, et c'est la partie
qui compte : un rôle accordé directement à un compte n'apparaît dans aucune
liste de groupes.

```bash
dsoxlab check iam-08-depart-collaborateur   # noter
dsoxlab hint  iam-08-depart-collaborateur   # un indice, au prix de quelques points
```
