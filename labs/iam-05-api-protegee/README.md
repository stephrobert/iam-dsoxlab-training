# Tutorial: three mechanisms to see at work

This tutorial does not do the challenge. It shows you the three mechanisms the
challenge needs, at work, on the measuring instruments the setup placed for you.
Nothing here declares `notes-api`, its scopes or the backup service: that is
the challenge.

## 1. What a scope puts in a token, and what it does not

Get a token with no particular scope, and read its audience:

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

`aud` says `account`. That is Keycloak's default, and it means the token is not
addressed to any API you declared. An API that compared `aud` to its own name
would refuse this token, which is correct: nobody said it was for it.

Now ask for the scope of the second API, the one the setup placed:

```bash
JETON2=$(curl -s -X POST "$KC/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=notes-cli \
  -d "username=$U" -d "password=$P" -d "scope=openid autre:lecture" \
  | jq -r .access_token)

charge "$JETON2" | jq '{aud, scope}'
```

`aud` now holds `autre-api` as well. **The scope did not do that by itself.**
The scope carries a protocol mapper, and that mapper is what writes the
audience. Look at it:

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

Read what you get: the scope has `include.in.token.scope` set, which is what
puts its name in the `scope` claim, and one mapper of type
`oidc-audience-mapper` naming `autre-api`. Two separate mechanisms, two
separate effects.

Finally, use that second token against the API:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8090/notes \
  -H "Authorization: Bearer $JETON2"
```

`200`. A token addressed to another API opens this one. The signature is
perfect, the issuer is right, the user is real, and the token is not yours.

## 2. 401 and 403 are not the same refusal

Both are refusals, and a client reacts to them differently. Try the two on a
service that has nothing to do with the challenge:

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

The first is `401`: the server does not know who you are, and it tells you how
to say so. The second is `403`: knowing who you are would change nothing.

An API behind tokens needs exactly this pair. A valid token with the wrong
permission is `403`, and answering `401` there would send the client into a
pointless loop of re-authentication.

## 3. A token with no user at all

A backup job has no human to log in. OAuth has a grant for that, and it needs
no user: the client authenticates as itself, with its secret.

Create a throwaway client to see it, and delete it right away:

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

Two things to notice, and both matter for the challenge.

`preferred_username` is `service-account-demo-machine`. Keycloak does give the
client an identity, and it names it for what it is: a service account, not a
person. Nobody typed a password to get this token.

And look at `scope`: `profile email`, which is what the client holds **by
default**. There is nobody here to ask for anything else, so nothing else
arrives. An optional scope would simply never appear in this token.

That is the trap. Attach the read permission as optional and the service gets a
token with no permission, while every test about human users keeps passing.

## What the challenge asks now

You have seen that an audience comes from a mapper and not from a scope name,
that `401` and `403` answer two different questions, and that a machine token
only carries default scopes.

The challenge asks you to declare the API as its own audience, create one scope
per permission with the mapper that carries it, make the API check all four
claims and the scope, and give the backup service read access and nothing else.

```bash
dsoxlab check iam-05-api-protegee   # grade
dsoxlab hint  iam-05-api-protegee   # one hint, at the cost of points
```
