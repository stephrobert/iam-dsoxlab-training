# Tutoriel : trois mécanismes à voir fonctionner

Ce tutoriel ne fait pas le challenge. Il vous montre à l'œuvre les trois
mécanismes dont le challenge a besoin, sur les instruments de mesure que le
setup a posés pour vous. Rien ici ne déclare `notes-api`, ses scopes ni le
service de sauvegarde : c'est le challenge.

## 1. Ce qu'un scope met dans un jeton, et ce qu'il n'y met pas

Obtenez un jeton sans scope particulier, et lisez son audience :

```bash
IDS=/opt/iam-lab/identifiants-lab.txt
U=$(grep '^UTILISATEUR=' $IDS | cut -d= -f2)
P=$(grep '^MOT_DE_PASSE=' $IDS | cut -d= -f2)
KC=http://127.0.0.1:8080/realms/formation

charge() {
  local c=$(echo "$1" | cut -d. -f2)
  local pad=$(( (4 - ${#c} % 4) % 4 ))
  [ "$pad" -gt 0 ] && c="$c$(printf '=%.0s' $(seq 1 "$pad"))"
  echo "$c" | tr '_-' '/+' | base64 -d
}

JETON=$(curl -s -X POST "$KC/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=notes-cli \
  -d "username=$U" -d "password=$P" | jq -r .access_token)

charge "$JETON" | jq '{aud, scope}'
```

`aud` vaut `account`. C'est le défaut de Keycloak, et cela veut dire que le
jeton n'est adressé à aucune API que vous auriez déclarée. Une API qui
comparerait `aud` à son propre nom refuserait ce jeton, et elle aurait raison :
personne n'a dit qu'il était pour elle.

Demandez maintenant le scope de la seconde API, celle que le setup a posée :

```bash
JETON2=$(curl -s -X POST "$KC/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=notes-cli \
  -d "username=$U" -d "password=$P" -d "scope=openid autre:lecture" \
  | jq -r .access_token)

charge "$JETON2" | jq '{aud, scope}'
```

`aud` porte désormais `autre-api` en plus. **Ce n'est pas le scope qui a fait
cela tout seul.** Le scope porte un mappeur de protocole, et c'est ce mappeur
qui écrit l'audience. Regardez-le :

```bash
AU=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME:' /opt/socle-iam/secrets.yml | cut -d'"' -f2)
AP=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD:' /opt/socle-iam/secrets.yml | cut -d'"' -f2)
ADM=$(curl -s -X POST \
  http://127.0.0.1:8080/realms/master/protocol/openid-connect/token \
  -d grant_type=password -d client_id=admin-cli \
  -d "username=$AU" -d "password=$AP" | jq -r .access_token)

curl -s http://127.0.0.1:8080/admin/realms/formation/client-scopes \
  -H "Authorization: Bearer $ADM" \
  | jq '.[] | select(.name == "autre:lecture")
        | {name, attributes, protocolMappers}'
```

Lisez ce que vous obtenez : le scope porte `include.in.token.scope`, qui est ce
qui met son nom dans la revendication `scope`, et un mappeur de type
`oidc-audience-mapper` qui nomme `autre-api`. Deux mécanismes distincts, deux
effets distincts.

Servez-vous enfin de ce second jeton contre l'API :

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8090/notes \
  -H "Authorization: Bearer $JETON2"
```

`200`. Un jeton adressé à une autre API ouvre celle-ci. La signature est
parfaite, l'émetteur est le bon, l'utilisateur est réel, et le jeton n'est pas
le vôtre.

## 2. 401 et 403 ne sont pas le même refus

Les deux sont des refus, et un client y réagit différemment. Essayez les deux
sur un service qui n'a rien à voir avec le challenge :

```bash
docker run -d --name demo-codes -p 18081:80 nginx:1.29-alpine \
  >/dev/null
docker exec demo-codes sh -c \
  'printf "utilisateur:\$apr1\$Hs3cJoFT\$tQBnHO2.SAf61J.oZZKJC1\n" > /etc/nginx/.htpasswd'
docker exec demo-codes sh -c 'cat > /etc/nginx/conf.d/default.conf <<CONF
server {
  listen 80;
  location /prive { auth_basic "zone"; auth_basic_user_file /etc/nginx/.htpasswd; }
  location /interdit { deny all; }
  location / { return 200 "ouvert\n"; }
}
CONF'
docker exec demo-codes nginx -s reload

echo "sans identifiants sur une zone protegee :"
curl -s -o /dev/null -w '  %{http_code}\n' http://127.0.0.1:18081/prive
echo "sur une zone interdite a tous :"
curl -s -o /dev/null -w '  %{http_code}\n' http://127.0.0.1:18081/interdit
docker rm -f demo-codes >/dev/null
```

Le premier est `401` : le serveur ne sait pas qui vous êtes, et il vous dit
comment le lui dire. Le second est `403` : savoir qui vous êtes n'y changerait
rien.

Une API derrière des jetons a besoin exactement de ce couple. Un jeton valide
avec la mauvaise permission, c'est `403`, et répondre `401` enverrait le client
dans une boucle inutile de ré-authentification.

## 3. Un jeton sans aucun utilisateur

Une tâche de sauvegarde n'a personne pour se connecter. OAuth a un octroi pour
cela, et il n'a besoin d'aucun utilisateur : le client s'authentifie en tant que
lui-même, avec son secret.

Créez un client jetable pour le voir, et supprimez-le aussitôt :

```bash
curl -s -o /dev/null -X POST \
  http://127.0.0.1:8080/admin/realms/formation/clients \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d '{"clientId":"demo-machine","publicClient":false,
       "standardFlowEnabled":false,"serviceAccountsEnabled":true}'

ID=$(curl -s \
  'http://127.0.0.1:8080/admin/realms/formation/clients?clientId=demo-machine' \
  -H "Authorization: Bearer $ADM" | jq -r '.[0].id')
SECRET=$(curl -s \
  "http://127.0.0.1:8080/admin/realms/formation/clients/$ID/client-secret" \
  -H "Authorization: Bearer $ADM" | jq -r .value)

JETON3=$(curl -s -X POST "$KC/protocol/openid-connect/token" \
  -d grant_type=client_credentials -d client_id=demo-machine \
  -d "client_secret=$SECRET" | jq -r .access_token)

charge "$JETON3" | jq '{aud, scope, preferred_username}'

curl -s -o /dev/null -X DELETE \
  "http://127.0.0.1:8080/admin/realms/formation/clients/$ID" \
  -H "Authorization: Bearer $ADM"
echo "client jetable retire"
```

Deux choses à remarquer, et les deux comptent pour le challenge.

`preferred_username` vaut `service-account-demo-machine`. Keycloak donne bien
une identité au client, et il la nomme pour ce qu'elle est : un compte de
service, pas une personne. Personne n'a tapé de mot de passe pour obtenir ce
jeton.

Et regardez `scope` : `profile email`, c'est-à-dire ce que le client détient
**par défaut**. Il n'y a personne ici pour demander autre chose, donc rien
d'autre n'arrive. Un scope optionnel n'apparaîtrait simplement jamais dans ce
jeton.

## Ce que le challenge demande maintenant

Vous avez vu qu'une audience vient d'un mappeur et non du nom d'un scope, que
`401` et `403` répondent à deux questions différentes, et qu'un jeton machine
ne porte que les scopes par défaut.

Le challenge vous demande de déclarer l'API comme sa propre audience, de créer
un scope par permission avec le mappeur qui la porte, de faire vérifier à l'API
les quatre revendications et le scope, et de donner au service de sauvegarde un
accès en lecture et rien d'autre.

```bash
dsoxlab check iam-05-api-protegee   # noter
dsoxlab hint  iam-05-api-protegee   # un indice, au prix de quelques points
```
