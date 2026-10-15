#!/usr/bin/env bash
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/lab-revue/common2.sh
source vars.sh
dec() { cut -d. -f2 <<<"$1" | tr '_-' '/+' | { read -r s; while [ $(( ${#s} % 4 )) -ne 0 ]; do s="$s="; done; base64 -d <<<"$s"; } | jq -c '{aud,azp,resource_access}'; }
ADM=$(curl -s -X POST $KC/realms/master/protocol/openid-connect/token -d grant_type=password -d client_id=admin-cli -d username=admin -d password=admin | jq -r .access_token)
WID=$(curl -s -H "Accept: application/json" -H "Authorization: Bearer $ADM" $KC/admin/realms/entreprise/workflows | jq -r '.[0].id')
curl -s -o /dev/null -w "DELETE workflow: %{http_code}\n" -X DELETE -H "Authorization: Bearer $ADM" $KC/admin/realms/entreprise/workflows/$WID
curl -s -H "Accept: application/json" -H "Authorization: Bearer $ADM" $KC/admin/realms/entreprise/workflows | jq -c .

echo "== 1. mauvaise audience (URL avec autre port)"
kcadm create clients -r entreprise -s clientId=scim-bad -s publicClient=false -s serviceAccountsEnabled=true -s standardFlowEnabled=false -s fullScopeAllowed=false
BID=$(kcadm get clients -r entreprise -q clientId=scim-bad --fields id --format csv --noquotes)
kcadm add-roles -r entreprise --uusername service-account-scim-bad --cclientid realm-management --rolename manage-users
MU=$(kcadm get "clients/$RM/roles/manage-users" -r entreprise | jq -c '[{id,name}]')
kcadm create "clients/$BID/scope-mappings/clients/$RM" -r entreprise -b "$MU"
kcadm create "clients/$BID/protocol-mappers/models" -r entreprise -s name=aud -s protocol=openid-connect -s protocolMapper=oidc-audience-mapper \
  -s 'config."included.custom.audience"=http://localhost:8480/realms/entreprise/scim/v2' -s 'config."access.token.claim"=true' -s 'config."id.token.claim"=false'
BS=$(kcadm get "clients/$BID/client-secret" -r entreprise | jq -r .value)
TB=$(curl -s -X POST $KC/realms/entreprise/protocol/openid-connect/token -d grant_type=client_credentials -d client_id=scim-bad -d client_secret=$BS | jq -r .access_token)
dec "$TB"
curl -s -w "\nHTTP %{http_code}\n" -H "Authorization: Bearer $TB" -H "Accept: application/scim+json" $SC/Users | tail -c 220

echo "== 2. client public"
kcadm create clients -r entreprise -s clientId=cli-pub -s publicClient=true -s standardFlowEnabled=false -s directAccessGrantsEnabled=true
PID=$(kcadm get clients -r entreprise -q clientId=cli-pub --fields id --format csv --noquotes)
kcadm create "clients/$PID/protocol-mappers/models" -r entreprise -s name=aud -s protocol=openid-connect -s protocolMapper=oidc-audience-mapper \
  -s 'config."included.custom.audience"=http://localhost:8080/realms/entreprise/scim/v2' -s 'config."access.token.claim"=true' -s 'config."id.token.claim"=false'
kcadm create users -r entreprise -s username=gest.pub -s enabled=true
kcadm set-password -r entreprise --username gest.pub --new-password 'Pub-lab-2026'
kcadm add-roles -r entreprise --uusername gest.pub --cclientid realm-management --rolename manage-users
TP=$(curl -s -X POST $KC/realms/entreprise/protocol/openid-connect/token -d grant_type=password -d client_id=cli-pub -d username=gest.pub -d password=Pub-lab-2026 | jq -r .access_token)
dec "$TP"
curl -s -w "\nHTTP %{http_code}\n" -H "Authorization: Bearer $TP" -H "Accept: application/scim+json" $SC/Users | tail -c 220

echo "== 3. administrateur"
kcadm create users -r entreprise -s username=adm.scim -s enabled=true
kcadm add-roles -r entreprise --uusername adm.scim --cclientid realm-management --rolename realm-admin
AID=$(kcadm get users -r entreprise -q username=adm.scim --fields id --format csv --noquotes)
curl -s -w "\nGET HTTP %{http_code}\n" $SC/Users/$AID "${J[@]}" | tail -c 150
curl -s -w "\nPATCH HTTP %{http_code}\n" -X PATCH $SC/Users/$AID "${J[@]}" -d '{"schemas":["urn:ietf:params:scim:api:messages:2.0:PatchOp"],"Operations":[{"op":"replace","path":"active","value":false}]}'
curl -s -w "\nDELETE HTTP %{http_code}\n" -X DELETE $SC/Users/$AID "${J[@]}"
kcadm get users/$AID -r entreprise --fields username,enabled | jq -c .
echo "-- groupe admin"
curl -s -X POST $SC/Groups "${J[@]}" -d "{\"schemas\":[\"$SCH_GROUPE\"],\"displayName\":\"admins\"}" | jq -r .id > .gadm
GA=$(cat .gadm)
kcadm add-roles -r entreprise --gname admins --cclientid realm-management --rolename realm-admin
curl -s -w "\nGROUP PATCH HTTP %{http_code}\n" -X PATCH $SC/Groups/$GA "${J[@]}" -d '{"schemas":["urn:ietf:params:scim:api:messages:2.0:PatchOp"],"Operations":[{"op":"replace","path":"displayName","value":"admins2"}]}' | tail -c 200
curl -s -w "\nGROUP DELETE HTTP %{http_code}\n" -X DELETE $SC/Groups/$GA "${J[@]}" | tail -c 200
echo "-- utilisateur avec manage-users seulement (gest.pub), via SCIM"
GP=$(kcadm get users -r entreprise -q username=gest.pub --fields id --format csv --noquotes)
curl -s -w "\nPATCH HTTP %{http_code}\n" -X PATCH $SC/Users/$GP "${J[@]}" -d '{"schemas":["urn:ietf:params:scim:api:messages:2.0:PatchOp"],"Operations":[{"op":"replace","path":"active","value":false}]}' | tail -c 200
