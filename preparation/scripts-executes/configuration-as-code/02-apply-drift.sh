#!/usr/bin/env bash
set -uo pipefail
D=/tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-cac
cd "$D/lab"
source env.sh
kc() { docker exec cac-keycloak /opt/keycloak/bin/kcadm.sh "$@"; }
kc config credentials --server http://localhost:8080 --realm master --user admin --password admin

echo "=== A. secret manquant (aucune variable) ==="
( unset TF_VAR_boutique_secret; terraform plan -no-color -input=false 2>&1 | head -12 )

echo "=== B. garde-fou master ==="
terraform plan -no-color -input=false -var realm_name=master 2>&1 | head -14; echo "code=$?"

echo "=== C. plan initial ==="
terraform plan -no-color -input=false -out=tfplan 2>&1 | grep -E '^\s+(#|\+ (realm|client_id|name|role_ids))|^Plan:' | head -30
echo "=== D. apply ==="
terraform apply -no-color -input=false tfplan 2>&1 | tail -12
echo "=== E. verif kcadm ==="
kc get realms/formation --fields realm,displayName,accessTokenLifespan
kc get roles -r formation --fields name
kc get groups -r formation --fields name
kc get clients -r formation -q clientId=boutique --fields clientId,redirectUris,publicClient
echo "=== F. replan sans changement ==="
terraform plan -no-color -input=false -detailed-exitcode 2>&1 | tail -3; echo "exit=${PIPESTATUS[0]}"

echo "=== G. derive par kcadm ==="
BID=$(kc get clients -r formation -q clientId=boutique --fields id --format csv --noquotes)
kc update clients/$BID -r formation -s 'redirectUris=["*"]'
kc update realms/formation -s accessTokenLifespan=86400
kc create roles -r formation -s name=intrus
echo "=== H. detection ==="
terraform plan -no-color -input=false -detailed-exitcode 2>&1 | grep -vE '^\s*$' | sed -n 1,45p; echo "exit=${PIPESTATUS[0]}"
echo "=== I. refresh-only ==="
terraform plan -no-color -input=false -refresh-only 2>&1 | grep -E '^\s+[~+-]|Objects have changed|^Plan|^No changes' | head
echo "=== J. correction ==="
terraform apply -no-color -input=false -auto-approve 2>&1 | tail -4
kc get realms/formation --fields accessTokenLifespan
kc get clients/$BID -r formation --fields redirectUris
kc get roles -r formation --fields name
terraform plan -no-color -input=false -detailed-exitcode >/dev/null 2>&1; echo "exit final=$?"
