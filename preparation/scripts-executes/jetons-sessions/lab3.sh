#!/usr/bin/env bash
set -u
D=/tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-jetons
kcadm() { docker exec keycloak /opt/keycloak/bin/kcadm.sh "$@"; }
SECRET_API=$(cat "$D/secret2.txt")
KC=http://localhost:8080/realms/observation/protocol/openid-connect
echo "##### B1 jetons"
dec() {
  local s; s=$(cut -d. -f2 <<<"$1" | tr '_-' '/+')
  while [ $(( ${#s} % 4 )) -ne 0 ]; do s="$s="; done
  base64 -d <<<"$s"
}
login() {
  curl -s -X POST "$KC/token" -d grant_type=password -d client_id=cli-observation \
    -d username=alice -d password='Alice-lab-2026' -d scope=openid
}
RESP=$(login)
jq 'del(.access_token, .id_token, .refresh_token)' <<<"$RESP"
AT=$(jq -r .access_token <<<"$RESP"); RT=$(jq -r .refresh_token <<<"$RESP"); IDT=$(jq -r .id_token <<<"$RESP")
dec "$AT"  | jq '{typ, azp, aud, sid, ttl: (.exp - .iat)}'
dec "$IDT" | jq '{typ, aud, ttl: (.exp - .iat)}'
dec "$RT"  | jq '{typ, sid, ttl: (.exp - .iat)}'
echo "##### B2 refresh sans rotation"
refresh() {
  curl -s -X POST "$KC/token" -d grant_type=refresh_token -d client_id=cli-observation -d refresh_token="$1"
}
R1=$(refresh "$RT"); RT1=$(jq -r .refresh_token <<<"$R1")
[ "$RT1" = "$RT" ] && echo "même refresh token" || echo "nouveau refresh token émis"
refresh "$RT" | jq -c '{expires_in, error}'
echo "##### B3 rotation"
kcadm config credentials --server http://localhost:8080 --realm master --user admin --password admin
kcadm update realms/observation -s revokeRefreshToken=true -s refreshTokenMaxReuse=0
RESP=$(login); RT0=$(jq -r .refresh_token <<<"$RESP")
R1=$(refresh "$RT0"); RT1=$(jq -r .refresh_token <<<"$R1")
refresh "$RT0" | jq -c .
refresh "$RT1" | jq -c .
echo "##### B4 introspection"
RESP=$(login); AT=$(jq -r .access_token <<<"$RESP"); RT=$(jq -r .refresh_token <<<"$RESP")
curl -s -X POST "$KC/token/introspect" -u "api-demo:$SECRET_API" -d token="$AT" \
  | jq '{active, username, client_id, aud, scope}'
curl -s -X POST "$KC/token/introspect" -u "api-demo:$SECRET_API" -d token="jeton-invalide" | jq -c .
curl -s -o /dev/null -w "userinfo: %{http_code}\n" "$KC/userinfo" -H "Authorization: Bearer $AT"
USER_ID=$(kcadm get users -r observation -q username=alice --fields id --format csv --noquotes)
echo "sessions SSO ouvertes: $(kcadm get "users/$USER_ID/sessions" -r observation | jq length)"
kcadm get "users/$USER_ID/sessions" -r observation | jq '.[-1] | {username, clients}'
echo "##### B5 logout"
curl -s -o /dev/null -w "logout: %{http_code}\n" -X POST "$KC/logout" -d client_id=cli-observation -d refresh_token="$RT"
echo "sessions SSO ouvertes: $(kcadm get "users/$USER_ID/sessions" -r observation | jq length)"
refresh "$RT" | jq -c .
curl -s -X POST "$KC/token/introspect" -u "api-demo:$SECRET_API" -d token="$AT" | jq -c .
curl -s -o /dev/null -w "userinfo: %{http_code}\n" "$KC/userinfo" -H "Authorization: Bearer $AT"
dec "$AT" | jq -r '"exp dans le futur: \(.exp > now)"'
echo "##### B6 revoke (RFC 7009)"
RESP=$(login); AT=$(jq -r .access_token <<<"$RESP"); RT=$(jq -r .refresh_token <<<"$RESP")
curl -s -o /dev/null -w "revoke: %{http_code}\n" -X POST "$KC/revoke" -d client_id=cli-observation -d token="$RT" -d token_type_hint=refresh_token
refresh "$RT" | jq -c .
curl -s -X POST "$KC/token/introspect" -u "api-demo:$SECRET_API" -d token="$AT" | jq -c .
echo "##### B7 sessions utilisateur"
RESP=$(login); RESP=$(login)
echo "avant: $(kcadm get "users/$USER_ID/sessions" -r observation | jq length)"
kcadm create "users/$USER_ID/logout" -r observation
echo "après: $(kcadm get "users/$USER_ID/sessions" -r observation | jq length)"
