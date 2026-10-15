#!/usr/bin/env bash
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/lab-revue/common2.sh
source vars.sh
curl -s -X POST $SC/Users "${J[@]}" -d "{\"schemas\":[\"$SCH_USER\"],\"userName\":\"marc.leroy\",
  \"name\":{\"givenName\":\"Marc\",\"familyName\":\"Leroy\"},
  \"emails\":[{\"value\":\"marc.leroy@exemple.fr\",\"type\":\"work\",\"primary\":true}],
  \"active\":true,\"groups\":[{\"value\":\"$COMPTA\"}]}" | jq -r .id
kcadm set-password -r entreprise --username marc.leroy --new-password 'Marc-lab-2026'
kcadm create clients -r entreprise -s clientId=cli-revue -s publicClient=true \
  -s standardFlowEnabled=false -s directAccessGrantsEnabled=true

MARC=$(kcadm get users -r entreprise -q username=marc.leroy --fields id --format csv --noquotes)
echo "MARC=$MARC" >> vars.sh
RT=$(curl -s -X POST $KC/realms/entreprise/protocol/openid-connect/token -d grant_type=password \
  -d client_id=cli-revue -d username=marc.leroy -d password=Marc-lab-2026 -d scope=openid | jq -r .refresh_token)
echo "t_login_marc=$(date +%T)"
refresh() {
  curl -s -X POST $KC/realms/entreprise/protocol/openid-connect/token -d grant_type=refresh_token \
    -d client_id=cli-revue -d refresh_token="$RT" | jq -c '{expires_in,error,error_description}'
}
echo "sessions avant: $(kcadm get "users/$MARC/sessions" -r entreprise | jq length)"
echo "== desactivation"
curl -s -w "PATCH active=false: %{http_code}\n" -o /dev/null -X PATCH $SC/Users/$MARC "${J[@]}" \
  -d '{"schemas":["urn:ietf:params:scim:api:messages:2.0:PatchOp"],"Operations":[{"op":"replace","path":"active","value":false}]}'
echo "enabled: $(kcadm get "users/$MARC" -r entreprise --fields enabled | jq -r .enabled)"
echo "sessions après désactivation: $(kcadm get "users/$MARC/sessions" -r entreprise | jq length)"
refresh
echo "== logout"
kcadm create "users/$MARC/logout" -r entreprise
echo "sessions après logout: $(kcadm get "users/$MARC/sessions" -r entreprise | jq length)"
refresh
curl -s -o /dev/null -w "GET /Users/id: %{http_code}\n" $SC/Users/$MARC "${J[@]}"
curl -s -G $SC/Users "${J[@]}" --data-urlencode 'filter=active eq false' | jq -c '[.Resources[].userName]'
echo "== Claire login (désactivée)"
curl -s -X POST $KC/realms/entreprise/protocol/openid-connect/token -d grant_type=password \
  -d client_id=cli-revue -d username=claire.dubois -d password=Claire-lab-2026 | jq -c .
echo "== suite du sort de marc, attente 60s"
for i in 1 2 3 4 5 6; do sleep 10; echo "$(date +%T) marc enabled=$(kcadm get users/$MARC -r entreprise --fields enabled | jq -r .enabled) grp=$(kcadm get users/$MARC/groups -r entreprise | jq -c '[.[].name]') mails=$(curl -s localhost:8025/api/v1/messages | jq -r .messages_count)"; done
docker logs keycloak 2>&1 | grep -E "marc|$MARC" | grep -iE "workflow|Disabling|Notification|Scheduled" | cut -c12-200
