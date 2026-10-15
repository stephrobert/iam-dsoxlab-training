#!/usr/bin/env bash
set -e
IMG='quay.io/keycloak/keycloak:26.7.0@sha256:0f198be292568439d700cdbfb893e69a6009bb43a94a06a945b1d3d506c76b13'
docker run -d --name kc-jetons -p 8080:8080 \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=admin -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin \
  "$IMG" start-dev
for i in $(seq 1 90); do
  curl -sf http://localhost:8080/realms/master >/dev/null && break
  sleep 2
done
curl -sf http://localhost:8080/realms/master >/dev/null && echo "Keycloak prêt"
K="docker exec kc-jetons /opt/keycloak/bin/kcadm.sh"
$K config credentials --server http://localhost:8080 --realm master --user admin --password admin
$K create realms -s realm=lab -s enabled=true
$K create users -r lab -s username=alice -s enabled=true -s firstName=Alice -s lastName=Martin -s email=alice@exemple.fr -s emailVerified=true
$K set-password -r lab --username alice --new-password 'Alice-lab-2026'
$K create clients -r lab -s clientId=cli-observation -s enabled=true -s publicClient=true -s standardFlowEnabled=false -s directAccessGrantsEnabled=true
echo SETUP-OK
