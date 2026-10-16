# Tutoriel : trois mécanismes à voir fonctionner

Ce tutoriel ne fait pas le challenge. Il vous montre à l'œuvre les trois
mécanismes dont le challenge a besoin, sur le partenaire qui tourne déjà et sur
un groupe jetable. Rien ici ne déclare le fournisseur d'identité.

Lisez d'abord les coordonnées du lab :

```bash
cat /opt/iam-lab/identifiants-lab.txt
```

## 1. Ce que le partenaire publie, et ce qu'il ne publie pas

Un partenaire avec qui vous fédérez vous remet trois choses : une URL de
découverte, un identifiant de client, et un secret. Tout le reste, vous le
lisez :

```bash
DEC=$(grep '^DECOUVERTE_PARTENAIRE=' /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)
curl -s "$DEC" | jq '{issuer, authorization_endpoint, token_endpoint,
                      userinfo_endpoint, jwks_uri}'
```

Cinq adresses, toutes dérivées d'une seule URL. Les taper à la main est la façon
dont une fédération casse le jour où le partenaire déplace quelque chose.

Regardez maintenant les clés, qui sont la partie qui vaut d'être comprise :

```bash
JWKS=$(curl -s "$DEC" | jq -r .jwks_uri)
curl -s "$JWKS" | jq '{nombre: (.keys | length),
                       ids: [.keys[].kid], usages: [.keys[].use]}'
```

Plusieurs clés, chacune avec un identifiant. Un fournisseur les fait tourner :
il en publie une nouvelle, signe avec elle, et garde l'ancienne le temps que les
jetons en vol expirent. Si votre courtier **lit** cette adresse, il suit cette
rotation sans que personne ne fasse rien. Si quelqu'un a collé une clé dans un
champ à la place, la fédération fonctionne jusqu'à la rotation, puis s'arrête,
un jour où personne n'a rien changé.

## 2. Un groupe par défaut appartient au realm

Créez un groupe jetable et regardez ce qu'il fait tout seul :

```bash
KC=http://127.0.0.1:8080
U=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME=' /opt/socle-iam/.env | cut -d= -f2-)
P=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD=' /opt/socle-iam/.env | cut -d= -f2-)
ADM=$(curl -s -X POST "$KC/realms/master/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  -d "username=$U" -d "password=$P" | jq -r .access_token)

curl -s -o /dev/null -w 'groupe : HTTP %{http_code}\n' -X POST \
  "$KC/admin/realms/formation/groups" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d '{"name":"demo-tuto"}'

echo "les groupes par defaut du realm :"
curl -s "$KC/admin/realms/formation/default-groups" \
  -H "Authorization: Bearer $ADM" | jq -c '[.[].name]'
```

Une liste vide. Le groupe existe et le realm ne sait pas qu'il doit s'en servir.
Créez un compte maintenant, et regardez :

```bash
curl -s -o /dev/null -X POST "$KC/admin/realms/formation/users" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d '{"username":"demo-avant","enabled":true}'
ID=$(curl -s "$KC/admin/realms/formation/users?username=demo-avant&exact=true" \
  -H "Authorization: Bearer $ADM" | jq -r '.[0].id')
curl -s "$KC/admin/realms/formation/users/$ID/groups" \
  -H "Authorization: Bearer $ADM" | jq -c '[.[].name]'
```

Rien. Dites-le maintenant au realm, et créez un second compte :

```bash
GID=$(curl -s "$KC/admin/realms/formation/groups" \
  -H "Authorization: Bearer $ADM" \
  | jq -r '.[] | select(.name=="demo-tuto") | .id')
curl -s -o /dev/null -w 'default-groups : HTTP %{http_code}\n' -X PUT \
  "$KC/admin/realms/formation/default-groups/$GID" \
  -H "Authorization: Bearer $ADM"

curl -s -o /dev/null -X POST "$KC/admin/realms/formation/users" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d '{"username":"demo-apres","enabled":true}'
ID2=$(curl -s "$KC/admin/realms/formation/users?username=demo-apres&exact=true" \
  -H "Authorization: Bearer $ADM" | jq -r '.[0].id')
echo "le compte cree APRES :"
curl -s "$KC/admin/realms/formation/users/$ID2/groups" \
  -H "Authorization: Bearer $ADM" | jq -c '[.[].name]'
echo "et le compte cree AVANT, relu :"
curl -s "$KC/admin/realms/formation/users/$ID/groups" \
  -H "Authorization: Bearer $ADM" | jq -c '[.[].name]'
```

Le second compte est dans le groupe. Le premier est toujours dehors, et il y
restera : un groupe par défaut s'applique **à la création**, et le déclarer plus
tard ne change rien aux comptes qui existent déjà.

Cela vaut d'être retenu, parce que c'est exactement ce qui arrive quand on
dépanne ceci. Vous vous connectez, le compte n'a pas de groupe, vous ajoutez le
groupe par défaut, vous vous reconnectez, et le compte n'a toujours pas de
groupe, parce que c'est le même compte. Supprimez-le et reconnectez-vous à neuf.

Nettoyez :

```bash
for n in demo-avant demo-apres; do
  I=$(curl -s "$KC/admin/realms/formation/users?username=$n&exact=true" \
    -H "Authorization: Bearer $ADM" | jq -r '.[0].id')
  curl -s -o /dev/null -X DELETE "$KC/admin/realms/formation/users/$I" \
    -H "Authorization: Bearer $ADM"
done
curl -s -o /dev/null -X DELETE \
  "$KC/admin/realms/formation/default-groups/$GID" -H "Authorization: Bearer $ADM"
curl -s -o /dev/null -X DELETE "$KC/admin/realms/formation/groups/$GID" \
  -H "Authorization: Bearer $ADM"
echo "nettoye"
```

## 3. Ce que fait vraiment le flux de premier login

Un flux est une liste d'étapes. Lisez celle que Keycloak vous donne pour un
compte qui arrive de l'extérieur pour la première fois :

```bash
curl -s "$KC/admin/realms/formation/authentication/flows/first%20broker%20login/executions" \
  -H "Authorization: Bearer $ADM" \
  | jq -r '.[] | "\(.requirement)\t\(.providerId // "-")\t\(.displayName)"' \
  | head -10
```

Lisez les quatre premières lignes comme une décision.

`idp-create-user-if-unique` crée le compte quand rien ne correspond. Il est
`ALTERNATIVE`, ce qui veut dire : essaie ceci, et si cela ne s'applique pas,
essaie la suite.

La suite est `Handle Existing Account`, et dessous se trouvent
`idp-confirm-link`, `REQUIRED`, puis des options de vérification. Autrement dit :
une adresse qui existe déjà ne produit **pas** une liaison. Elle produit une
question, puis une preuve.

C'est la partie du challenge qui vous demande de ne rien faire. Il existe un
fournisseur nommé `idp-auto-link` qui saute tout cela, et son seul effet est de
remettre à un inconnu le compte local qui se trouve partager son adresse.
Savoir qu'il existe, et le laisser tranquille, c'est le travail.

Vous verrez le refus à la notation : l'un des deux comptes du partenaire
s'arrête sur un écran qui nomme le conflit. Cet écran est la preuve.

## Ce que le challenge demande maintenant

Vous avez vu qu'un partenaire publie tout sauf son secret, qu'un groupe par
défaut est une propriété du realm et s'applique à la création, et que le flux de
premier login pose une question là où un flux négligent remettrait un compte.

Le challenge demande le fournisseur d'identité, le groupe par défaut, et un flux
de premier login que vous n'avez pas affaibli.

```bash
dsoxlab check iam-11-federation-externe   # noter
dsoxlab hint  iam-11-federation-externe   # un indice, au prix de quelques points
```
