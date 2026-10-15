#!/usr/bin/env bash
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/lab-revue/common.sh
curl -s -X DELETE localhost:8025/api/v1/messages -o /dev/null -w "purge mailpit %{http_code}\n"
kcadm create realms -r master -s realm=essai -s enabled=true
kcadm update realms/essai -s 'smtpServer={"host":"mailpit","port":"1025","from":"iam@exemple.fr"}'
kcadm create groups -r essai -s name=desactives
kcadm create clients -r essai -s clientId=scim-client -s publicClient=false -s serviceAccountsEnabled=true
kcadm create users -r essai -s username=u1 -s enabled=true -s firstName=U -s lastName=Un -s email=u1@exemple.fr
KC=http://localhost:8080
ADM=$(curl -s -X POST $KC/realms/master/protocol/openid-connect/token -d grant_type=password -d client_id=admin-cli -d username=admin -d password=admin | jq -r .access_token)
echo "T0 $(date +%T)"
curl -s -i -X POST $KC/admin/realms/essai/workflows -H "Authorization: Bearer $ADM" -H "Content-Type: application/yaml" --data-binary @sans-if.yaml | head -1
for i in $(seq 1 14); do
  SA=$(kcadm get users -r essai -q username=service-account-scim-client --fields enabled | jq -c '.[0].enabled')
  U1=$(kcadm get users -r essai -q username=u1 --fields enabled | jq -c '.[0].enabled')
  echo "$(date +%T) sa_enabled=$SA u1_enabled=$U1 courriels=$(curl -s localhost:8025/api/v1/messages | jq -r .messages_count)"
  sleep 8
done
echo "-- destinataires"; curl -s localhost:8025/api/v1/messages | jq -r '.messages[]|.To[0].Address' | sort | uniq -c
echo "-- activations/boucle"
docker logs keycloak 2>&1 | grep -E "activated|completed" | awk '$0 ~ /19:4[89]|19:5/' | cut -c1-24,100-240
