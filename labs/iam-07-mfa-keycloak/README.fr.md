# Tutoriel : trois mécanismes à voir fonctionner

Ce tutoriel ne fait pas le challenge. Il vous montre les trois mécanismes dont
le challenge a besoin, en lisant ce que Keycloak offre déjà et en faisant une
copie jetable que vous supprimez à la fin.

```bash
KC=http://127.0.0.1:8080
U=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME=' /opt/socle-iam/.env | cut -d= -f2-)
P=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD=' /opt/socle-iam/.env | cut -d= -f2-)
ADM=$(curl -s -X POST "$KC/realms/master/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  -d "username=$U" -d "password=$P" | jq -r .access_token)
```

## 1. Quelles conditions existent, et laquelle n'existe pas

Une étape de flux peut être conditionnelle. Demandez à Keycloak quelles
conditions il possède :

```bash
curl -s "$KC/admin/realms/formation/authentication/authenticator-providers" \
  -H "Authorization: Bearer $ADM" \
  | jq -r '.[] | select(.id | startswith("conditional-")) | "\(.id)\t\(.displayName)"'
```

Lisez cette liste avec attention, et remarquez ce qui n'y est **pas**. Il y a
une condition sur un rôle, sur un attribut d'utilisateur, sur un identifiant,
sur un scope de client. Il n'y a aucune condition sur un **groupe**.

Cela compte, parce que les équipes sont des groupes. La voie est un rôle : le
groupe porte le rôle, et la condition teste le rôle. Vérifiez qu'un groupe peut
en porter un :

```bash
curl -s "$KC/admin/realms/formation/groups" -H "Authorization: Bearer $ADM" \
  | jq -r '.[] | "\(.name)\t\(.id)"'
```

Et retenez ceci pour vérifier votre travail : un rôle porté par un groupe
n'apparaît **pas** dans les rôles directs d'un compte. Il apparaît dans ses
rôles effectifs :

```bash
ID=$(curl -s "$KC/admin/realms/formation/users?username=resp-exploitation&exact=true" \
  -H "Authorization: Bearer $ADM" | jq -r '.[0].id')
echo "directs   :"
curl -s "$KC/admin/realms/formation/users/$ID/role-mappings" \
  -H "Authorization: Bearer $ADM" | jq -c '[.realmMappings[]?.name]'
echo "effectifs :"
curl -s "$KC/admin/realms/formation/users/$ID/role-mappings/realm/composite" \
  -H "Authorization: Bearer $ADM" | jq -c '[.[].name]'
```

## 2. Ce que contient une copie du flux de navigateur

Copiez le flux, sous un nom jetable, et lisez ce que vous obtenez :

```bash
curl -s -o /dev/null -w 'copie : HTTP %{http_code}\n' -X POST \
  "$KC/admin/realms/formation/authentication/flows/browser/copy" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d '{"newName":"demo-tuto"}'

curl -s "$KC/admin/realms/formation/authentication/flows/demo-tuto/executions" \
  -H "Authorization: Bearer $ADM" \
  | jq -r '.[] | "niveau=\(.level)\t\(.requirement)\t\(.providerId // "-")\t\(.displayName)"'
```

Lisez l'indentation que `niveau` vous donne. Il y a **deux** sous-flux
conditionnels, et chacun a sa propre `conditional-user-configured` :

- l'un sous *Conditional Organization*, qui n'a rien à voir avec les seconds
  facteurs ;
- l'autre sous *Conditional 2FA*, qui est celui dont parle le challenge.

Cela vaut d'être vu maintenant, parce que retirer la mauvaise laisse le piège en
place et casse autre chose. Le sous-flux a sa propre adresse :

```bash
curl -s "$KC/admin/realms/formation/authentication/flows/demo-tuto%20Browser%20-%20Conditional%202FA/executions" \
  -H "Authorization: Bearer $ADM" \
  | jq -r '.[] | "\(.requirement)\t\(.providerId // "-")\t\(.displayName)"'
```

Quatre lignes, et c'est tout le sujet : une condition, une condition
d'identifiant, le formulaire de code, et deux options éteintes.

## 3. Ce que « user configured » veut dire vraiment

`conditional-user-configured` se lit, en entier : *n'applique ce sous-flux que
si l'utilisateur a DÉJÀ configuré l'identifiant qu'il demande*.

Relisez-le. Cela veut dire que le second facteur est demandé aux gens qui en ont
un, et sauté pour ceux qui n'en ont pas. Pour un compte sans second facteur,
tout le sous-flux est sauté, y compris l'étape que vous avez mise en `REQUIRED`.

C'est pour cela que la console peut montrer un flux avec un second facteur
dedans alors que personne ne s'en voit demander un. Le réglage est juste,
l'effet est nul, et aucun message ne le dit nulle part.

Supprimez la copie jetable. Notez l'adresse : un flux se supprime par son
**identifiant**, et non par son nom, là où ses exécutions se lisent par son
**nom**. L'incohérence est celle de Keycloak, et une suppression par nom répond
404 sans rien supprimer :

```bash
ID_FLUX=$(curl -s "$KC/admin/realms/formation/authentication/flows" \
  -H "Authorization: Bearer $ADM" \
  | jq -r '.[] | select(.alias=="demo-tuto") | .id')
curl -s -o /dev/null -w 'suppression : HTTP %{http_code}\n' -X DELETE \
  "$KC/admin/realms/formation/authentication/flows/$ID_FLUX" \
  -H "Authorization: Bearer $ADM"
curl -s "$KC/admin/realms/formation/authentication/flows" \
  -H "Authorization: Bearer $ADM" | jq -c '[.[] | select(.builtIn == false) | .alias]'
```

Une liste vide. Si elle ne l'est pas, quelque chose d'un essai précédent est
encore là, et votre prochaine copie échouera sur un conflit de nom déjà pris.

## Ce que le challenge demande maintenant

Vous avez vu qu'il n'existe aucune condition de groupe, qu'une copie du flux de
navigateur porte deux sous-flux conditionnels, et que « user configured » veut
dire le contraire de ce qu'on espère.

Le challenge demande une copie, une condition de rôle sur le bon sous-flux, le
retrait de celle qui l'annule, une option résistante au hameçonnage, et une
politique de mot de passe qui fait confiance à la longueur plutôt qu'à la
composition.

```bash
dsoxlab check iam-07-mfa-keycloak   # noter
dsoxlab hint  iam-07-mfa-keycloak   # un indice, au prix de quelques points
```
