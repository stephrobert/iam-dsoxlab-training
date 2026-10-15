#!/usr/bin/env bash
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/lab-revue/common2.sh
source vars.sh
curl -s -X POST $SC/Groups "${J[@]}" -d "{\"schemas\":[\"$SCH_GROUPE\"],\"displayName\":\"desactives\"}" | jq -c '{displayName,id}'
kcadm update realms/entreprise -s 'smtpServer={"host":"mailpit","port":"1025","from":"iam@exemple.fr"}'
kcadm set-password -r entreprise --username claire.dubois --new-password 'Claire-lab-2026'

ADM=$(curl -s -X POST $KC/realms/master/protocol/openid-connect/token \
  -d grant_type=password -d client_id=admin-cli -d username=admin -d password=admin | jq -r .access_token)
echo "T0 depot $(date +%T)"
curl -s -i -X POST $KC/admin/realms/entreprise/workflows \
  -H "Authorization: Bearer $ADM" -H "Content-Type: application/yaml" \
  --data-binary @comptes-inactifs.yaml | head -2
curl -s -H "Accept: application/json" -H "Authorization: Bearer $ADM" \
  $KC/admin/realms/entreprise/workflows | jq -c '.[] | {name, on, steps: [.steps[].uses]}'
USER_ID=$USER_ID
for i in $(seq 1 12); do
  EN=$(kcadm get "users/$USER_ID" -r entreprise --fields enabled | jq -r .enabled)
  GR=$(kcadm get "users/$USER_ID/groups" -r entreprise | jq -c '[.[].name]')
  MS=$(curl -s http://localhost:8025/api/v1/messages | jq -r .messages_count)
  echo "$(date +%T) enabled=$EN groupes=$GR courriels=$MS"; sleep 6
done
docker logs keycloak 2>&1 | grep -E "Workflow 'comptes-inactifs'|Disabling user|Notification email" | cut -c12-210
