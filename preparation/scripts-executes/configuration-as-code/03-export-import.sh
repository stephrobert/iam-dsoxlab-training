#!/usr/bin/env bash
set -uo pipefail
D=/tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-cac
cd "$D/lab"
source env.sh
kc() { docker exec cac-keycloak /opt/keycloak/bin/kcadm.sh "$@"; }
kc config credentials --server http://localhost:8080 --realm master --user admin --password admin

echo "=== K. secret dans les fichiers versionnables ? ==="
grep -c "$TF_VAR_boutique_secret" main.tf variables.tf versions.tf
echo "=== L. secret dans le state ? ==="
grep -c "$TF_VAR_boutique_secret" terraform.tfstate
ls -l terraform.tfstate

echo "=== M. export partiel ==="
kc create realms/formation/partial-export -s exportClients=true -s exportGroupsAndRoles=true -o > ../export-formation.json 2>/dev/null
wc -c ../export-formation.json
jq -r '.realm, (.roles.realm | map(.name) | join(",")), (.groups | map(.name) | join(",")), (.clients[] | select(.clientId=="boutique") | .secret, .redirectUris[0])' ../export-formation.json

echo "=== N. import + generate-config-out dans un dossier vide ==="
rm -rf ../lab-import && mkdir ../lab-import && cd ../lab-import
cp ../lab/versions.tf .
cat > import.tf <<'EOF'
import {
  to = keycloak_realm.formation
  id = "formation"
}

import {
  to = keycloak_openid_client.boutique
  id = "formation/07bc048c-18ab-466e-993b-4a4188a2ed56"
}
EOF
terraform init -no-color 2>&1 | tail -2
terraform plan -no-color -input=false -generate-config-out=generated.tf 2>&1 | tail -12
wc -l generated.tf
grep -nE 'client_secret|access_token_lifespan|valid_redirect_uris|realm +=|password' generated.tf | head
