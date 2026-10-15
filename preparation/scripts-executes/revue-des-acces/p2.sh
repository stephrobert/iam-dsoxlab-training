#!/usr/bin/env bash
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/lab-revue/common.sh
echo "== avant activation"
curl -s -o /dev/null -w "avant activation: %{http_code}\n" $SC/ServiceProviderConfig
kcadm get realms/entreprise --fields scimApiEnabled
kcadm update realms/entreprise -s scimApiEnabled=true
curl -s -o /dev/null -w "sans jeton: %{http_code}\n" http://localhost:8080/realms/entreprise/scim/v2/ServiceProviderConfig
curl -s -i http://localhost:8080/realms/entreprise/scim/v2/ServiceProviderConfig | head -12

kcadm create clients -r entreprise -s clientId=scim-client -s publicClient=false \
  -s serviceAccountsEnabled=true -s standardFlowEnabled=false -s fullScopeAllowed=false
CID=$(kcadm get clients -r entreprise -q clientId=scim-client --fields id --format csv --noquotes)
RM=$(kcadm get clients -r entreprise -q clientId=realm-management --fields id --format csv --noquotes)
kcadm add-roles -r entreprise --uusername service-account-scim-client \
  --cclientid realm-management --rolename manage-users
MU=$(kcadm get "clients/$RM/roles/manage-users" -r entreprise | jq -c '[{id,name}]')
kcadm create "clients/$CID/scope-mappings/clients/$RM" -r entreprise -b "$MU"
kcadm get "clients/$CID/client-secret" -r entreprise | jq -j .value > .scim-secret
chmod 600 .scim-secret
echo "CID=$CID" > vars.sh; echo "RM=$RM" >> vars.sh

echo "== jeton SANS audience (avant mapper)"
T0=$(curl -s -X POST $KC/realms/entreprise/protocol/openid-connect/token \
    -d grant_type=client_credentials -d client_id=scim-client \
    --data-urlencode "client_secret@.scim-secret" | jq -r .access_token)
cut -d. -f2 <<<"$T0" | tr '_-' '/+' | { read -r s; while [ $(( ${#s} % 4 )) -ne 0 ]; do s="$s="; done; base64 -d <<<"$s"; } | jq -c '{aud, resource_access}'
curl -s -i -H "Authorization: Bearer $T0" -H "Accept: application/scim+json" $SC/ServiceProviderConfig | head -12
echo
curl -s -H "Authorization: Bearer $T0" -H "Accept: application/scim+json" $SC/Users | head -c 400; echo

kcadm create "clients/$CID/protocol-mappers/models" -r entreprise \
  -s name=scim-audience -s protocol=openid-connect -s protocolMapper=oidc-audience-mapper \
  -s 'config."included.custom.audience"=http://localhost:8080/realms/entreprise/scim/v2' \
  -s 'config."access.token.claim"=true' -s 'config."id.token.claim"=false'

tok() {
  curl -s -X POST $KC/realms/entreprise/protocol/openid-connect/token \
    -d grant_type=client_credentials -d client_id=scim-client \
    --data-urlencode "client_secret@.scim-secret" | jq -r .access_token
}
T=$(tok)
cut -d. -f2 <<<"$T" | tr '_-' '/+' | { read -r s; while [ $(( ${#s} % 4 )) -ne 0 ]; do s="$s="; done; base64 -d <<<"$s"; } \
  | jq '{aud, azp, resource_access}'
curl -s -H "Authorization: Bearer $T" -H "Accept: application/scim+json" $SC/ServiceProviderConfig \
  | jq -c '{patch, filter, bulk, sort}'
curl -s -H "Authorization: Bearer $T" -H "Accept: application/scim+json" $SC/ServiceProviderConfig | jq -c '.filter, .patch'
