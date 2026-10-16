#!/usr/bin/env bash
set -u
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-production/lib.sh

echo "##### Preparation du realm formation (kcadm dans le conteneur, port 8080 interne)"
docker compose exec -T keycloak sh -c '/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user temp-admin --password "$KC_BOOTSTRAP_ADMIN_PASSWORD"'
kcadm create realms -s realm=formation -s enabled=true
kcadm create users -r formation -s username=alice -s enabled=true -s firstName=Alice -s lastName=Martin -s email=alice@exemple.fr
kcadm set-password -r formation --username alice --new-password 'Alice-lab-2026'
kcadm create clients -r formation -s clientId=appli -s publicClient=true -s directAccessGrantsEnabled=true -s standardFlowEnabled=true -s 'redirectUris=["https://appli.lab.test/*"]'

echo
echo "##### 1. Document de decouverte via le proxy public"
cpub -o $D/discovery.json -w 'HTTP %{http_code}\n' $PUB/realms/formation/.well-known/openid-configuration
jq -r '.issuer, .authorization_endpoint, .token_endpoint, .jwks_uri' $D/discovery.json
echo "-- valeurs-URL qui ne commencent PAS par l'adresse publique :"
jq -r '[.. | strings | select(test("^https?://"))] | map(select(startswith("https://auth.lab.test:18443/") | not)) | .[]' $D/discovery.json | sort -u
echo "-- nombre de valeurs http:// (non chiffrees) :"
jq -r '[.. | strings | select(startswith("http://"))] | length' $D/discovery.json
echo "-- nombre total de valeurs-URL :"
jq -r '[.. | strings | select(test("^https?://"))] | length' $D/discovery.json

echo
echo "##### 1b. Le Host de la requete ne change pas l'issuer (hostname strict)"
cmgmt -H 'Host: evil.test' -H 'X-Forwarded-Host: evil.test' http://localhost:8080/realms/formation/.well-known/openid-configuration | jq -r .issuer

echo
echo "##### 1c. Jeton obtenu par l'adresse publique : claim iss"
TOKEN=$(cpub -X POST $PUB/realms/formation/protocol/openid-connect/token -d grant_type=password -d client_id=appli -d username=alice -d password='Alice-lab-2026' -d scope=openid)
echo "$TOKEN" | jq -r .access_token | cut -d. -f2 | tr '_-' '/+' | { read -r s; while [ $(( ${#s} % 4 )) -ne 0 ]; do s="$s="; done; echo "$s" | base64 -d; } | jq -c '{iss, azp, typ}'

echo
echo "##### 2. Console d'administration : adresse publique"
for p in /admin/master/console/ /admin/ /realms/master/.well-known/openid-configuration /health/ready /metrics / /realms/formation/.well-known/openid-configuration; do
  printf '%-55s' "public $p"; cpub -o /dev/null -w '%{http_code}\n' "$PUB$p"
done
echo "-- adresse d'administration"
for p in /admin/master/console/ /realms/master/.well-known/openid-configuration; do
  printf '%-55s' "admin $p"; cadm -o /dev/null -w '%{http_code}\n' "$ADM$p"
done
echo "-- issuer du realm master vu depuis l'adresse d'administration :"
cadm $ADM/realms/master/.well-known/openid-configuration | jq -r .issuer
echo "-- la console sur le nom public (hors proxy, Host public) redirige-t-elle ?"
cmgmt -o /dev/null -D - -H 'Host: auth.lab.test:18443' -H 'X-Forwarded-Proto: https' -H 'X-Forwarded-Host: auth.lab.test:18443' http://localhost:8080/admin/ | grep -i -E '^HTTP|^location'

echo
echo "##### 3. Port 9000"
echo "-- depuis le reseau du conteneur Keycloak"
cmgmt http://localhost:9000/health/ready; echo
cmgmt -o /dev/null -w 'live HTTP %{http_code}\n' http://localhost:9000/health/live
cmgmt http://localhost:9000/metrics | grep -E '^(jvm_memory_used_bytes|keycloak_)' | head -4
echo "-- depuis l'hote"
curl -sS -m 3 -o /dev/null -w 'hote 127.0.0.1:9000 -> %{http_code}\n' http://127.0.0.1:9000/health/ready 2>&1 | tail -1
curl -sS -m 3 -o /dev/null -w 'hote 127.0.0.1:8080 -> %{http_code}\n' http://127.0.0.1:8080/realms/master 2>&1 | tail -1
echo "-- ports publies par Compose"
docker compose ps --format '{{.Service}} {{.Ports}}'
echo "-- port 8080 interne : /health"
cmgmt -o /dev/null -w '8080 /health/ready -> %{http_code}\n' http://localhost:8080/health/ready
