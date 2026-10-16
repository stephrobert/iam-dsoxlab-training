# Tutoriel : trois mécanismes à voir fonctionner

Ce tutoriel ne fait pas le challenge. Il vous montre à l'œuvre les trois
mécanismes dont le challenge a besoin, sur un compte jetable qui n'est aucun des
trois que vous devez créer.

Lisez d'abord les coordonnées de l'annuaire :

```bash
cat /opt/iam-lab/identifiants-lab.txt
BASE=$(grep '^BASE_DN=' /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)
ADMIN=$(grep '^ADMIN_DN=' /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)
MDP=$(grep '^ADMIN_MOT_DE_PASSE=' /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)
echo "base : $BASE"
```

Remarquez `cut -d= -f2-`, avec le tiret. Le DN de base vaut
`dc=formation,dc=lab` : il contient le séparateur, et `-f2` seul vous rendrait
`dc`. Toutes les requêtes échoueraient alors sur `Naming violation (64):
Missing DN value`, qui désigne la requête et non la variable qui l'a fabriquée.

## 1. Ce qui est déjà dans l'arbre

Demandez à l'annuaire ce qu'il contient, avant d'écrire quoi que ce soit :

```bash
ldapsearch -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" \
  -b "$BASE" -LLL '(objectClass=*)' dn
```

Trois groupes et un compte, tous appartenant à l'annuaire lui-même. Et notez ce
qui n'est **pas** listé : `ou=people` et `ou=groups` ne sont pas des entrées que
vous pouvez voir ou créer. LLDAP impose cette disposition. Vous n'organiserez
pas l'arbre, vous le remplirez.

Regardez l'administrateur en entier, et les classes d'objet que LLDAP donne à un
compte :

```bash
ldapsearch -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" \
  -b "$BASE" -LLL '(uid=admin)'
```

`inetOrgPerson`, `posixAccount`, `mailAccount`, `person`. Vous en déclarez une
en créant un compte ; l'annuaire ajoute les autres.

## 2. Écrire, et relire aussitôt

Créez un compte jetable, puis relisez-le immédiatement. Relire après chaque
écriture est l'habitude que ce lab existe pour installer :

```bash
cat > /tmp/demo.ldif <<LDIF
dn: uid=demo-tuto,ou=people,$BASE
objectClass: inetOrgPerson
uid: demo-tuto
cn: Démo Tutoriel
sn: Tutoriel
mail: demo-tuto@formation.lab
LDIF

ldapadd -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" -f /tmp/demo.ldif
ldapsearch -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" \
  -b "$BASE" -LLL '(uid=demo-tuto)'
```

Deux choses dans cette sortie.

Le `cn` est revenu en `cn:: RMOpbW8gVHV0b3JpZWw=`, avec un **double
deux-points**. C'est le LDIF qui dit « cette valeur est en base64 », parce
qu'elle n'est pas de l'ASCII simple. Décodez pour en être sûr :

```bash
echo 'RMOpbW8gVHV0b3JpZWw=' | base64 -d; echo
```

Elle est juste. L'un des comptes que vous devez créer porte un accent, et son
`cn` reviendra de la même façon. Décoder avant de conclure épargne une heure.

Et LLDAP a ajouté un attribut de son cru, `last_name`, à côté du `sn` que vous
avez déclaré. Un annuaire léger garde son propre modèle et y projette le vôtre.

## 3. L'appartenance, et l'écriture qui ment

Créez un groupe jetable et essayez d'y mettre le compte par le seul LDIF,
exactement comme un serveur LDAP le permettrait d'ordinaire :

```bash
cat > /tmp/demo-grp.ldif <<LDIF
dn: cn=demo-grp,ou=groups,$BASE
objectClass: groupOfNames
cn: demo-grp
member: uid=demo-tuto,ou=people,$BASE
LDIF

ldapadd -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" -f /tmp/demo-grp.ldif
echo "--- et le membre, relu ---"
ldapsearch -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" \
  -b "ou=groups,$BASE" -LLL '(cn=demo-grp)' member
```

**L'ajout a réussi, et le groupe n'a aucun membre.** Aucun avertissement,
aucune erreur : la ligne `member:` a été acceptée et jetée. C'est le refus qui
ressemble à un succès, et relire est le seul moyen de le voir.

Essayez l'autre voie évidente, modifier le groupe :

```bash
cat > /tmp/demo-mod.ldif <<LDIF
dn: cn=demo-grp,ou=groups,$BASE
changetype: modify
add: member
member: uid=demo-tuto,ou=people,$BASE
LDIF
ldapmodify -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" -f /tmp/demo-mod.ldif
```

`Invalid DN syntax (34)`, et le message dit `Invalid username: Unexpected DN
format. Got "cn=demo-grp,…", expected "uid=id,ou=people,…"`. LLDAP a lu le DN du
groupe comme s'il était celui d'une personne. Le message égare, et la conclusion
est claire : ici, les appartenances ne passent pas par LDAP.

Elles passent par l'API de l'annuaire. Obtenez un jeton, listez les groupes pour
trouver l'identifiant numérique que l'API emploie, et ajoutez le membre :

```bash
WEB=http://127.0.0.1:17170
JETON=$(curl -s -X POST "$WEB/auth/simple/login" \
  -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg m "$MDP" '{username:"admin", password:$m}')" | jq -r .token)

GID=$(curl -s -X POST "$WEB/api/graphql" \
  -H "Authorization: Bearer $JETON" -H 'Content-Type: application/json' \
  -d '{"query":"{ groups { id displayName } }"}' \
  | jq -r '.data.groups[] | select(.displayName == "demo-grp") | .id')
echo "id du groupe : $GID"

curl -s -X POST "$WEB/api/graphql" \
  -H "Authorization: Bearer $JETON" -H 'Content-Type: application/json' \
  -d "$(jq -nc --argjson g "$GID" '{query:"mutation($u: String!, $g: Int!) { addUserToGroup(userId: $u, groupId: $g) { ok } }", variables:{u:"demo-tuto", g:$g}}')"
echo
```

Relisez maintenant, des deux côtés :

```bash
ldapsearch -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" \
  -b "ou=groups,$BASE" -LLL '(cn=demo-grp)' member uniqueMember
ldapsearch -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" \
  -b "ou=people,$BASE" -LLL '(uid=demo-tuto)' memberOf
```

`member`, `uniquemember` et `memberOf` sont tous servis désormais. L'API l'a
écrit, et LDAP le lit : c'est le partage avec lequel vous travaillez.

Une dernière chose à savoir. L'API répond HTTP `200` **avec** un tableau
`errors` quand un appel échoue. Ne regarder que le code de statut ferait passer
un appel en échec pour un succès :

```bash
curl -s -X POST "$WEB/api/graphql" \
  -H "Authorization: Bearer $JETON" -H 'Content-Type: application/json' \
  -d '{"query":"mutation { addUserToGroup(userId: \"personne-inexistante\", groupId: 1) { ok } }"}' \
  -o /tmp/reponse -w 'code HTTP : %{http_code}\n'
cat /tmp/reponse; echo
```

Nettoyez les objets jetables :

```bash
curl -s -o /dev/null -X POST "$WEB/api/graphql" \
  -H "Authorization: Bearer $JETON" -H 'Content-Type: application/json' \
  -d "$(jq -nc --argjson g "$GID" '{query:"mutation($g: Int!) { deleteGroup(groupId: $g) { ok } }", variables:{g:$g}}')"
ldapdelete -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" \
  "uid=demo-tuto,ou=people,$BASE"
rm -f /tmp/demo.ldif /tmp/demo-grp.ldif /tmp/demo-mod.ldif /tmp/reponse
echo "nettoye"
```

## Ce que le challenge demande maintenant

Vous avez vu que l'arbre est imposé, que le LDIF rend du base64 pour tout ce
qui n'est pas de l'ASCII simple, et que les appartenances passent par l'API
quand tout le reste passe par LDAP.

Le challenge demande trois personnes, deux groupes, des appartenances exactes,
et la preuve que tout cela survit à un redémarrage.

```bash
dsoxlab check iam-01-annuaire-lldap   # noter
dsoxlab hint  iam-01-annuaire-lldap   # un indice, au prix de quelques points
```
