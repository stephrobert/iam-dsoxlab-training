#!/usr/bin/env bash
cd "$(dirname "$0")"
kcp() { docker exec keycloak-partenaire /opt/keycloak/bin/kcadm.sh "$@"; }
kc() { docker exec keycloak /opt/keycloak/bin/kcadm.sh "$@"; }
CID=$(kcp get clients -r partenaire -q clientId=portail-entreprise --fields id --format csv --noquotes)
kcp update clients/$CID -r partenaire -s 'redirectUris=["http://localhost:8080/realms/lab/broker/partenaire/endpoint"]'
kc update identity-provider/instances/partenaire -r lab -s config.clientSecret=mauvais-secret
echo "--- connexion de bruno avec secret faux"
J=$(mktemp)
L=$(curl -s -o /dev/null -D - -c $J -b $J "http://localhost:8080/realms/lab/protocol/openid-connect/auth?client_id=app-interne&response_type=code&scope=openid&redirect_uri=http://localhost:9999/cb&kc_idp_hint=partenaire" | grep -i '^location' | tr -d '\r' | cut -d' ' -f2-)
L2=$(curl -s -o /dev/null -D - -c $J -b $J "$L" | grep -i '^location' | tr -d '\r' | cut -d' ' -f2-)
A=$(curl -s -c $J -b $J "$L2" | grep -o 'action="[^"]*"' | head -1 | sed 's/action="//; s/"$//; s/&amp;/\&/g')
R=$(curl -s -o /dev/null -D - -c $J -b $J --data-urlencode username=bruno --data-urlencode password=Bruno-lab-2026 "$A" | grep -i '^location' | tr -d '\r' | cut -d' ' -f2-)
curl -s -o p4.html -w 'HTTP %{http_code}\n' -c $J -b $J -L "$R"
sed 's/<[^>]*>/ /g' p4.html | tr -s ' \n' | grep -v '^ *$' | grep -i 'error\|unexpected\|sorry\|identity' | head -5
grep -o '<title>[^<]*' p4.html
echo "--- journal broker"
docker logs keycloak 2>&1 | grep -i 'unauthorized\|status=\|identity provider' | tail -4 | cut -c1-600
