#!/usr/bin/env bash
kcp() { docker exec keycloak-partenaire /opt/keycloak/bin/kcadm.sh "$@"; }
kcp config credentials --server http://localhost:8082 --realm master --user admin --password admin 2>&1|tail -1
CID=$(kcp get clients -r partenaire -q clientId=portail-entreprise --fields id --format csv --noquotes); echo $CID
for URI in "http://localhost:8080/realms/lab/broker/partenaire/endpoin" "http://localhost:8080/realms/lab/broker/Partenaire/endpoint" "http://localhost:8080/realms/lab/broker/partenaire/endpoint"; do
 echo "=== $URI"
 kcp update clients/$CID -r partenaire -s "redirectUris=[\"$URI\"]"
 bash login.sh bruno Bruno-lab-2026 2>&1 | head -4
 grep -o '<title>[^<]*' last-page.html | head -3
 grep -A3 'kc-error-message' last-page.html | sed 's/<[^>]*>//g' | tr -s ' \n'
done
