#!/usr/bin/env bash
cd "$(dirname "$0")"
kc() { docker exec keycloak /opt/keycloak/bin/kcadm.sh "$@"; }
kc get 'authentication/flows/first%20broker%20login/executions' -r lab \
  | jq -r '.[] | select(.level <= 2) | "\(.level) \(.displayName) [\(.requirement)]"'
echo "--- remise en visibilité par hideOnLogin=false"
kc update identity-provider/instances/partenaire -r lab -s hideOnLogin=false
kc get identity-provider/instances/partenaire -r lab | jq -c '{hideOnLogin}'
curl -s "http://localhost:8080/realms/lab/protocol/openid-connect/auth?client_id=app-interne&response_type=code&scope=openid&redirect_uri=http://localhost:9999/cb" | grep -o 'id="social-[a-z]*"'
