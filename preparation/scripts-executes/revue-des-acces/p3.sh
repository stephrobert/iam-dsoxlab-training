#!/usr/bin/env bash
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/lab-revue/common2.sh
COMPTA=$(curl -s -X POST $SC/Groups "${J[@]}" -d "{\"schemas\":[\"$SCH_GROUPE\"],\"displayName\":\"compta\"}" | jq -r .id)
DEV=$(curl -s -X POST $SC/Groups "${J[@]}" -d "{\"schemas\":[\"$SCH_GROUPE\"],\"displayName\":\"dev\"}" | jq -r .id)
echo "COMPTA=$COMPTA DEV=$DEV"
echo "COMPTA=$COMPTA" >> vars.sh; echo "DEV=$DEV" >> vars.sh

U="{\"schemas\":[\"$SCH_USER\"],
  \"userName\":\"claire.dubois\",\"name\":{\"givenName\":\"Claire\",\"familyName\":\"Dubois\"},
  \"emails\":[{\"value\":\"claire.dubois@exemple.fr\",\"type\":\"work\",\"primary\":true}],
  \"active\":true,\"groups\":[{\"value\":\"$COMPTA\"}]}"
curl -s -w "\nHTTP %{http_code}\n" -X POST $SC/Users "${J[@]}" -d "$U"
echo "== rejeu"
curl -s -w "\nHTTP %{http_code}\n" -X POST $SC/Users "${J[@]}" -d "$U"
echo "== recherche ordinaire"
curl -s -G $SC/Users "${J[@]}" --data-urlencode 'filter=userName eq "claire.dubois"' | jq -c '.Resources[0]'

USER_ID=$(kcadm get users -r entreprise -q username=claire.dubois --fields id --format csv --noquotes)
echo "USER_ID=$USER_ID" >> vars.sh
curl -s -G $SC/Users "${J[@]}" --data-urlencode 'filter=userName eq "claire.dubois"' \
  --data-urlencode 'attributes=userName,groups' | jq -c '.Resources[0]'
kcadm get "users/$USER_ID/groups" -r entreprise | jq -c '[.[].name]'

echo "== PATCH mobilité"
curl -s -w "HTTP %{http_code}\n" -o /dev/null -X PATCH $SC/Users/$USER_ID "${J[@]}" -d "{
  \"schemas\":[\"urn:ietf:params:scim:api:messages:2.0:PatchOp\"],
  \"Operations\":[{\"op\":\"remove\",\"path\":\"groups[value eq \\\"$COMPTA\\\"]\"},
                  {\"op\":\"add\",\"path\":\"groups\",\"value\":\"$DEV\"}]}"
kcadm get "users/$USER_ID/groups" -r entreprise | jq -c '[.[].name]'
curl -s -G $SC/Users "${J[@]}" --data-urlencode 'filter=active eq true' | jq -c '[.Resources[].userName]'
