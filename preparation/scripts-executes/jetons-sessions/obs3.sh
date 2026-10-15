#!/usr/bin/env bash
set -u
D=/tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-jetons
KC=http://localhost:8080/realms/lab/protocol/openid-connect
K="docker exec kc-jetons /opt/keycloak/bin/kcadm.sh"
SECRET=$(cat $D/secret.txt)
$K config credentials --server http://localhost:8080 --realm master --user admin --password admin >/dev/null
$K create realms/lab/logout-all 2>&1 | head -2
UID_=$($K get users -r lab -q username=alice --fields id --format csv --noquotes)
CIDO=$($K get clients -r lab -q clientId=cli-observation --fields id --format csv --noquotes)
echo "sessions au départ: $($K get users/$UID_/sessions -r lab | jq length)"
tok() { curl -s -X POST $KC/token -d grant_type=password -d client_id=cli-observation -d username=alice -d password='Alice-lab-2026' -d scope=openid; }
RESP=$(tok); AT=$(jq -r .access_token <<<"$RESP")
echo "-- introspect sans audience"
curl -s -X POST $KC/token/introspect -u "api-demo:$SECRET" -d token="$AT" | jq -c '{active}'
echo "-- mapper audience"
$K create clients/$CIDO/protocol-mappers/models -r lab -s name=aud-api-demo -s protocol=openid-connect -s protocolMapper=oidc-audience-mapper -s 'config."included.client.audience"=api-demo' -s 'config."access.token.claim"=true' -s 'config."id.token.claim"=false'
RESP=$(tok); AT=$(jq -r .access_token <<<"$RESP"); RT=$(jq -r .refresh_token <<<"$RESP")
echo "sessions: $($K get users/$UID_/sessions -r lab | jq length)"
echo "-- introspect avec audience"
curl -s -X POST $KC/token/introspect -u "api-demo:$SECRET" -d token="$AT" | jq -c '{active,username,scope,client_id,aud,exp,sid}'
echo "-- userinfo: $(curl -s -o /dev/null -w '%{http_code}' $KC/userinfo -H "Authorization: Bearer $AT")"
echo "== revoke RT"
curl -s -o /dev/null -w "revoke http=%{http_code}\n" -X POST $KC/revoke -d client_id=cli-observation -d token="$RT" -d token_type_hint=refresh_token
echo "-- introspect AT après revoke RT"
curl -s -X POST $KC/token/introspect -u "api-demo:$SECRET" -d token="$AT" | jq -c '{active}'
echo "-- userinfo: $(curl -s -o /dev/null -w '%{http_code}' $KC/userinfo -H "Authorization: Bearer $AT")"
echo "sessions: $($K get users/$UID_/sessions -r lab | jq length)"
echo "== logout test"
RESP=$(tok); AT=$(jq -r .access_token <<<"$RESP"); RT=$(jq -r .refresh_token <<<"$RESP"); IDT=$(jq -r .id_token <<<"$RESP")
echo "sessions avant logout: $($K get users/$UID_/sessions -r lab | jq length)"
curl -s -o /dev/null -w "logout http=%{http_code}\n" -X POST $KC/logout -d client_id=cli-observation -d refresh_token="$RT"
echo "sessions après logout: $($K get users/$UID_/sessions -r lab | jq length)"
echo "-- refresh après logout:"
curl -s -X POST $KC/token -d grant_type=refresh_token -d client_id=cli-observation -d refresh_token="$RT" | jq -c .
echo "-- AT toujours valide localement (exp futur), introspect:"
curl -s -X POST $KC/token/introspect -u "api-demo:$SECRET" -d token="$AT" | jq -c '{active}'
echo "-- userinfo: $(curl -s -o /dev/null -w '%{http_code}' $KC/userinfo -H "Authorization: Bearer $AT")"
echo "== GET logout (id_token_hint)"
RESP=$(tok); IDT=$(jq -r .id_token <<<"$RESP")
curl -s -o /dev/null -w "GET logout http=%{http_code}\n" "$KC/logout?id_token_hint=$IDT&client_id=cli-observation"
echo "sessions: $($K get users/$UID_/sessions -r lab | jq length)"
