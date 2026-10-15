#!/usr/bin/env bash
set -u
KC=http://localhost:8080/realms/lab/protocol/openid-connect
K="docker exec kc-jetons /opt/keycloak/bin/kcadm.sh"
$K config credentials --server http://localhost:8080 --realm master --user admin --password admin >/dev/null
echo "== rotation ON"
$K update realms/lab -s revokeRefreshToken=true -s refreshTokenMaxReuse=0
tok() { curl -s -X POST $KC/token -d grant_type=password -d client_id=cli-observation -d username=alice -d password='Alice-lab-2026' -d scope=openid; }
RESP=$(tok); RT0=$(jq -r .refresh_token <<<"$RESP")
R1=$(curl -s -X POST $KC/token -d grant_type=refresh_token -d client_id=cli-observation -d refresh_token="$RT0")
RT1=$(jq -r .refresh_token <<<"$R1")
[ "$RT1" = "$RT0" ] && echo "identique" || echo "NOUVEAU refresh token"
echo "-- rejeu de l'ancien RT0:"
curl -s -X POST $KC/token -d grant_type=refresh_token -d client_id=cli-observation -d refresh_token="$RT0" | jq .
echo "-- le RT1 (légitime) marche encore ?"
curl -s -X POST $KC/token -d grant_type=refresh_token -d client_id=cli-observation -d refresh_token="$RT1" | jq 'del(.access_token,.id_token,.refresh_token)'
echo "== introspection : client confidentiel"
$K create clients -r lab -s clientId=api-demo -s enabled=true -s publicClient=false -s standardFlowEnabled=false -s serviceAccountsEnabled=true
CID=$($K get clients -r lab -q clientId=api-demo --fields id --format csv --noquotes)
SECRET=$($K get clients/$CID/client-secret -r lab | jq -r .value)
RESP=$(tok); AT=$(jq -r .access_token <<<"$RESP"); RT=$(jq -r .refresh_token <<<"$RESP")
echo "-- introspect (token valide)"
curl -s -X POST $KC/token/introspect -u "api-demo:$SECRET" -d token="$AT" -d token_type_hint=access_token | jq '{active,username,scope,client_id,exp,sid}'
echo "== sessions SSO côté IdP"
UID_=$($K get users -r lab -q username=alice --fields id --format csv --noquotes)
$K get users/$UID_/sessions -r lab | jq '.[0]|{id,username,start,lastAccess,clients}'
echo "== userinfo avec AT"
curl -s -o /dev/null -w "%{http_code}\n" $KC/userinfo -H "Authorization: Bearer $AT"
echo "== revoke refresh token (RFC 7009)"
curl -s -o /dev/null -w "revoke http=%{http_code}\n" -X POST $KC/revoke -d client_id=cli-observation -d token="$RT" -d token_type_hint=refresh_token
echo "-- refresh après revoke:"
curl -s -X POST $KC/token -d grant_type=refresh_token -d client_id=cli-observation -d refresh_token="$RT" | jq .
echo "-- AT introspect après revoke du RT:"
curl -s -X POST $KC/token/introspect -u "api-demo:$SECRET" -d token="$AT" | jq '{active}'
echo "-- userinfo après revoke du RT:"
curl -s -o /dev/null -w "%{http_code}\n" $KC/userinfo -H "Authorization: Bearer $AT"
echo "-- sessions après revoke:"
$K get users/$UID_/sessions -r lab | jq 'length'
echo "$SECRET" > /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-jetons/secret.txt
