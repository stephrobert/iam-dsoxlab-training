#!/usr/bin/env bash
cd "$(dirname "$0")"
kcp() { docker exec keycloak-partenaire /opt/keycloak/bin/kcadm.sh "$@"; }
CID=$(kcp get clients -r partenaire -q clientId=portail-entreprise --fields id --format csv --noquotes)
for URI in "http://localhost:8080/realms/lab/broker/partenaire/endpoin" "http://localhost:8080/realms/lab/broker/Partenaire/endpoint"; do
 echo "=== client: $URI"
 kcp update clients/$CID -r partenaire -s "redirectUris=[\"$URI\"]"
 J=$(mktemp)
 L=$(curl -s -o /dev/null -D - -c $J -b $J "http://localhost:8080/realms/lab/protocol/openid-connect/auth?client_id=app-interne&response_type=code&scope=openid&redirect_uri=http://localhost:9999/cb&kc_idp_hint=partenaire" | grep -i '^location' | tr -d '\r' | cut -d' ' -f2-)
 L2=$(curl -s -o /dev/null -D - -c $J -b $J "$L" | grep -i '^location' | tr -d '\r' | cut -d' ' -f2-)
 curl -s -o p.html -w 'HTTP %{http_code}\n' -c $J -b $J "$L2"
 sed 's/<[^>]*>/ /g' p.html | tr -s ' \n' | grep -v '^ *$' | grep -iv 'const\|function\|{\|}' | head -8
done
docker logs keycloak-partenaire 2>&1 | grep -i 'redirect' | tail -3 | cut -c1-500
