#!/usr/bin/env bash
set -uo pipefail
D=/tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-cac
cd "$D/lab"
kc() { docker exec cac-keycloak /opt/keycloak/bin/kcadm.sh "$@"; }
kc config credentials --server http://localhost:8080 --realm master --user admin --password admin

echo "=== O. secret stable dans un fichier hors dépôt ==="
( umask 077; openssl rand -hex 16 | tr -d '\n' > "$D/boutique.secret" )
ls -l "$D/boutique.secret"
cat > env.sh <<'EOF'
export KEYCLOAK_URL=http://localhost:18180
export KEYCLOAK_CLIENT_ID=admin-cli
export KEYCLOAK_USER=admin
export KEYCLOAK_PASSWORD=admin
export TF_VAR_boutique_secret="$(cat ../boutique.secret)"
EOF
source env.sh
echo "--- apply avec le nouveau secret (rotation) ---"
terraform plan -no-color -input=false 2>&1 | grep -E 'client_secret|Plan:|No changes|updated in-place'
terraform apply -no-color -input=false -auto-approve 2>&1 | tail -2
echo "--- secret dans le state ? (compte) ---"
grep -c "$TF_VAR_boutique_secret" terraform.tfstate
echo "--- secret côté Keycloak == fichier ? ---"
BID=$(kc get clients -r formation -q clientId=boutique --fields id --format csv --noquotes)
[ "$(kc get clients/$BID/client-secret -r formation | jq -r .value)" = "$TF_VAR_boutique_secret" ] && echo identique
echo "--- secret dans les .tf ? ---"
grep -c "$TF_VAR_boutique_secret" main.tf variables.tf versions.tf

echo "=== M. export partiel (query params) ==="
kc create realms/formation/partial-export -q exportClients=true -q exportGroupsAndRoles=true -o > ../export-formation.json 2>/dev/null
wc -c ../export-formation.json
jq -r '"realm: " + .realm, ("roles: " + (.roles.realm | map(.name) | join(","))), ("groupes: " + (.groups | map(.name) | join(","))), (.clients[] | select(.clientId=="boutique") | "secret exporté: " + .secret, "redirect: " + .redirectUris[0])' ../export-formation.json

echo "=== N. import + generate-config-out ==="
rm -rf ../lab-import && mkdir ../lab-import && cd ../lab-import
cp ../lab/versions.tf ../lab/.terraform.lock.hcl .
cat > import.tf <<EOF
import {
  to = keycloak_realm.formation
  id = "formation"
}

import {
  to = keycloak_openid_client.boutique
  id = "formation/$BID"
}
EOF
terraform init -no-color 2>&1 | grep -E 'Using|success'
terraform plan -no-color -input=false -generate-config-out=generated.tf 2>&1 | tail -8
wc -l generated.tf
grep -nE 'client_secret|access_token_lifespan|valid_redirect_uris|^resource|realm +=' generated.tf | head -12
