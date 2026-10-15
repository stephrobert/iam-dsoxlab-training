#!/usr/bin/env bash
set -u
D=/tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-jetons
# Bloc 0b : préparer le realm
kcadm() { docker exec keycloak /opt/keycloak/bin/kcadm.sh "$@"; }
kcadm config credentials --server http://localhost:8080 --realm master --user admin --password admin
kcadm create realms -s realm=observation -s enabled=true
kcadm create users -r observation -s username=alice -s enabled=true \
  -s firstName=Alice -s lastName=Martin -s email=alice@exemple.fr
kcadm set-password -r observation --username alice --new-password 'Alice-lab-2026'
kcadm create clients -r observation -s clientId=cli-observation -s publicClient=true \
  -s standardFlowEnabled=false -s directAccessGrantsEnabled=true
kcadm create clients -r observation -s clientId=api-demo -s publicClient=false \
  -s standardFlowEnabled=false
CLI_ID=$(kcadm get clients -r observation -q clientId=cli-observation --fields id --format csv --noquotes)
kcadm create "clients/$CLI_ID/protocol-mappers/models" -r observation \
  -s name=audience-api-demo -s protocol=openid-connect -s protocolMapper=oidc-audience-mapper \
  -s 'config."included.client.audience"=api-demo' \
  -s 'config."access.token.claim"=true' -s 'config."id.token.claim"=false'
API_ID=$(kcadm get clients -r observation -q clientId=api-demo --fields id --format csv --noquotes)
kcadm get "clients/$API_ID/client-secret" -r observation | jq -r .value > "$D/secret2.txt"
echo "secret: $(wc -c < "$D/secret2.txt") octets"
echo "== durées du realm"
kcadm get realms/observation --fields accessTokenLifespan,ssoSessionIdleTimeout,ssoSessionMaxLifespan,revokeRefreshToken
kcadm get realms/master --fields accessTokenLifespan
