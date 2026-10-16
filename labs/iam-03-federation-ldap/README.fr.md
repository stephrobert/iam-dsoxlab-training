# Tutoriel : trois mécanismes à voir fonctionner

Ce tutoriel ne fait pas le challenge. Il vous montre à l'œuvre les trois
mécanismes dont le challenge a besoin, et il commence par celui qui fait perdre
le plus de temps.

## 1. Le localhost d'un conteneur est le sien

Les deux services tournent dans des conteneurs. Regardez ce que le conteneur du
fournisseur peut réellement joindre :

```bash
for nom in lldap socle-iam-lldap-1 127.0.0.1; do
  echo -n "$nom resout : "
  docker exec socle-iam-keycloak-1 getent hosts "$nom" 2>/dev/null \
    | head -1 || echo "(rien)"
done
```

Trois noms résolvent, et ce n'est pas la question. La question est lequel répond
sur le port de l'annuaire :

```bash
for nom in lldap 127.0.0.1; do
  if docker exec socle-iam-keycloak-1 \
       sh -c "timeout 3 bash -c 'echo > /dev/tcp/$nom/3890'" 2>/dev/null; then
    echo "$nom:3890 ouvert"
  else
    echo "$nom:3890 ferme"
  fi
done
```

`127.0.0.1:3890` est fermé. Pas filtré, pas lent : il n'y a rien, parce que dans
ce conteneur `127.0.0.1` est le conteneur.

Et pourtant, depuis la machine elle-même, la même adresse fonctionne
parfaitement :

```bash
BASE=$(grep '^BASE_DN=' /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)
ADMIN=$(grep '^ADMIN_DN=' /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)
MDP=$(grep '^ADMIN_MOT_DE_PASSE=' /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)
ldapwhoami -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP"
```

C'est tout le piège. Vous essayez l'adresse depuis votre shell, elle marche,
vous la collez dans la configuration du fournisseur, et le fournisseur ne peut
pas l'atteindre. L'adresse qu'on donne à un service doit être joignable
**depuis ce service**.

## 2. Ce que l'annuaire publie vraiment

Avant de configurer quoi que ce soit, regardez ce que la fédération devra lire.
C'est l'information que chaque champ de la configuration réclame :

```bash
echo "--- un compte ---"
ldapsearch -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" \
  -b "ou=people,$BASE" -LLL '(uid=aline)'
echo "--- un groupe ---"
ldapsearch -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" \
  -b "ou=groups,$BASE" -LLL '(cn=devops)'
```

Lisez-le comme une liste de réponses.

L'identifiant est `uid`, pas `cn` et pas `mail` : c'est l'attribut de nom
d'utilisateur. La classe d'objet est `inetOrgPerson`. La branche est
`ou=people`. Côté groupe, les membres sont listés dans `member`, **sous forme
de DN complets**, et non d'identifiants nus : la configuration a un champ à part
pour cette distinction.

Et remarquez `entryuuid`. C'est un identifiant que l'annuaire attribue et ne
change jamais, même si l'entrée est renommée. Un DN change quand l'identifiant
de quelqu'un change ; celui-ci, non. Dire à la fédération de s'y appuyer, c'est
ce qui garde un compte renommé rattaché à ses sessions au lieu de le faire
arriver comme une nouvelle personne.

## 3. Déclarer n'importe rien

Une fédération est un composant du realm. Créez-en une jetable, exprès avec la
mauvaise adresse, et regardez ce que dit la synchronisation :

```bash
KC=http://127.0.0.1:8080
U=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME=' /opt/socle-iam/.env | cut -d= -f2-)
P=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD=' /opt/socle-iam/.env | cut -d= -f2-)
ADM=$(curl -s -X POST "$KC/realms/master/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  -d "username=$U" -d "password=$P" | jq -r .access_token)

ID_REALM=$(curl -s "$KC/admin/realms/formation" \
  -H "Authorization: Bearer $ADM" | jq -r .id)

curl -s -o /dev/null -w 'creation : HTTP %{http_code}\n' -X POST \
  "$KC/admin/realms/formation/components" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg base "$BASE" --arg dn "$ADMIN" --arg mdp "$MDP" \
        --arg parent "$ID_REALM" '{
    name:"demo-mauvaise-adresse", providerId:"ldap",
    providerType:"org.keycloak.storage.UserStorageProvider", parentId:$parent,
    config:{enabled:["true"], importEnabled:["true"], editMode:["READ_ONLY"],
            vendor:["other"], usernameLDAPAttribute:["uid"],
            rdnLDAPAttribute:["uid"], uuidLDAPAttribute:["entryUUID"],
            userObjectClasses:["inetOrgPerson"],
            connectionUrl:["ldap://127.0.0.1:3890"],
            usersDn:[("ou=people," + $base)], authType:["simple"],
            bindDn:[$dn], bindCredential:[$mdp], searchScope:["1"]}}')"

ID_DEMO=$(curl -s \
  "$KC/admin/realms/formation/components?parent=$ID_REALM&type=org.keycloak.storage.UserStorageProvider" \
  -H "Authorization: Bearer $ADM" \
  | jq -r '.[] | select(.name=="demo-mauvaise-adresse") | .id')

echo "--- la synchronisation ---"
curl -s -X POST \
  "$KC/admin/realms/formation/user-storage/$ID_DEMO/sync?action=triggerFullSync" \
  -H "Authorization: Bearer $ADM" | jq -c .
```

`0 imported users`, et le statut HTTP était un succès. C'est le seul signal que
vous obtenez. Aucune erreur, aucune ligne de journal qui vous crie dessus, rien
qui passe au rouge dans la console.

Essayez maintenant de ne changer que l'adresse. Relisez le composant, modifiez
le seul champ, et envoyez-le :

```bash
LU=$(curl -s "$KC/admin/realms/formation/components/$ID_DEMO" \
     -H "Authorization: Bearer $ADM")
echo "$LU" | jq -c '{connectionUrl: .config.connectionUrl,
                     bindCredential: .config.bindCredential}'

curl -s -o /dev/null -w 'PUT : HTTP %{http_code}\n' -X PUT \
  "$KC/admin/realms/formation/components/$ID_DEMO" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d "$(echo "$LU" | jq '.config.connectionUrl = ["ldap://lldap:3890"]')"
```

`HTTP 400`, et regardez ce que vous venez d'afficher : `bindCredential` est
revenu en `**********`. Keycloak ne rend pas les secrets qu'il garde, et il
refuse qu'on lui redonne ce masque comme valeur. Le refus est explicite ici, et
c'est une chance : un serveur qui l'aurait accepté aurait cassé la liaison, et
vous seriez revenu à `0 imported users` sans savoir pourquoi.

Remettez le vrai secret, et renvoyez :

```bash
curl -s -o /dev/null -w 'PUT : HTTP %{http_code}\n' -X PUT \
  "$KC/admin/realms/formation/components/$ID_DEMO" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d "$(echo "$LU" | jq --arg mdp "$MDP" \
        '.config.connectionUrl = ["ldap://lldap:3890"]
         | .config.bindCredential = [$mdp]')"

curl -s -X POST \
  "$KC/admin/realms/formation/user-storage/$ID_DEMO/sync?action=triggerFullSync" \
  -H "Authorization: Bearer $ADM" | jq -c .
```

Maintenant il importe. Un champ, et c'est la différence entre une fédération qui
fonctionne et une fédération qui ne voit personne en silence. Mesuré : quatre
comptes, parce que l'administrateur de l'annuaire en est un.

Regardez ce qui est arrivé, et ce qui ne l'est pas :

```bash
curl -s 'http://127.0.0.1:8080/admin/realms/formation/users?briefRepresentation=true' \
  -H "Authorization: Bearer $ADM" | jq -c '[.[] | {username, email}]'
echo "--- et les groupes ? ---"
curl -s http://127.0.0.1:8080/admin/realms/formation/groups \
  -H "Authorization: Bearer $ADM" | jq -c '[.[].name]'
```

Les comptes sont là. Les groupes **non**, et rejouer cette synchronisation ne
les fera pas venir. Les groupes viennent d'un second composant, avec sa propre
synchronisation, dans un sens explicite. C'est le troisième mécanisme, et le
challenge en a besoin.

Nettoyez la fédération jetable. La retirer retire aussi les comptes qu'elle a
importés, puisqu'ils n'existent dans Keycloak que par elle :

```bash
curl -s -o /dev/null -X DELETE \
  "$KC/admin/realms/formation/components/$ID_DEMO" \
  -H "Authorization: Bearer $ADM"
curl -s 'http://127.0.0.1:8080/admin/realms/formation/users?briefRepresentation=true' \
  -H "Authorization: Bearer $ADM" | jq -c '[.[].username]'
```

Une liste vide. C'est à retenir : un compte fédéré n'est pas une copie qu'il
faut nettoyer, c'est une vue qui disparaît avec sa source.

## Ce que le challenge demande maintenant

Vous avez vu qu'une adresse doit être joignable depuis le service qui s'en sert,
que l'annuaire répond à toutes les questions de la configuration si l'on lit une
entrée, et que déclarer une fédération n'importe rien tant qu'on ne le demande
pas.

Le challenge demande la fédération, en lecture seule, le mappeur de groupes, les
deux synchronisations, et une connexion avec un compte que le fournisseur n'a
jamais créé.

```bash
dsoxlab check iam-03-federation-ldap   # noter
dsoxlab hint  iam-03-federation-ldap   # un indice, au prix de quelques points
```
