#!/usr/bin/env bash
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/lab-revue/common.sh
while [ ! -f stop-mon ]; do
  E=$(kcadm get users -r entreprise -q username=service-account-scim-client --fields enabled 2>&1 | jq -c ".[0].enabled" 2>&1)
  M=$(curl -s http://localhost:8025/api/v1/messages | jq -r .messages_count)
  echo "$(date +%T) sa_enabled=$E mails=$M" >> monitor.log
  sleep 2
done
