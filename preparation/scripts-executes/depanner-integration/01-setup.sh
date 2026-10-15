#!/usr/bin/env bash
set -euo pipefail
. "$(dirname "$0")/common.sh"
docker run -d --name keycloak -p 8080:8080 \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \
  -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:26.7.0@sha256:0f198be292568439d700cdbfb893e69a6009bb43a94a06a945b1d3d506c76b13 \
  start-dev
until curl -sf http://localhost:8080/realms/master >/dev/null; do sleep 2; done
kcadm config credentials --server http://localhost:8080 --realm master --user admin --password admin
kcadm create realms -s realm=lab -s enabled=true
kcadm create users -r lab -s username=alice -s enabled=true \
  -s firstName=Alice -s lastName=Martin -s email=alice@exemple.fr
kcadm set-password -r lab --username alice --new-password 'Alice-lab-2026'
# événements de login
kcadm update events/config -r lab -s eventsEnabled=true -s 'eventsListeners=["jboss-logging"]' -s eventsExpiration=3600
kcadm get events/config -r lab
# API + scopes
kcadm create clients -r lab -s clientId=notes-api -s publicClient=false -s standardFlowEnabled=false
for scope in notes:lecture notes:ecriture; do
  SID=$(kcadm create client-scopes -r lab -s "name=$scope" -s protocol=openid-connect \
    -s 'attributes."include.in.token.scope"=true' -i)
  kcadm create "client-scopes/$SID/protocol-mappers/models" -r lab \
    -s name=audience-notes-api -s protocol=openid-connect \
    -s protocolMapper=oidc-audience-mapper \
    -s 'config."included.client.audience"=notes-api' \
    -s 'config."access.token.claim"=true' -s 'config."id.token.claim"=false'
done
CLI=$(kcadm create clients -r lab -s clientId=notes-cli -s publicClient=true \
  -s standardFlowEnabled=false -s directAccessGrantsEnabled=true -i)
for scope in notes:lecture notes:ecriture; do
  SID=$(kcadm get client-scopes -r lab --fields id,name --format csv --noquotes | grep ",$scope\$" | cut -d, -f1)
  kcadm update "clients/$CLI/optional-client-scopes/$SID" -r lab
done
# application web confidentielle (code flow)
kcadm create clients -r lab -s clientId=boutique -s publicClient=false \
  -s standardFlowEnabled=true -s 'redirectUris=["http://localhost:3000/callback"]'
echo SETUP OK
