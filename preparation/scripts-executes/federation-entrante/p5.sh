#!/usr/bin/env bash
cd "$(dirname "$0")"
kc() { docker exec keycloak /opt/keycloak/bin/kcadm.sh "$@"; }
kc update identity-provider/instances/partenaire -r lab -s "config.clientSecret=$(cat secret.txt)"
echo "--- avant masquage, sans hint"
curl -s "http://localhost:8080/realms/lab/protocol/openid-connect/auth?client_id=app-interne&response_type=code&scope=openid&redirect_uri=http://localhost:9999/cb" -o q0.html -w 'HTTP %{http_code}\n'
grep -o 'id="social-[a-z]*"' q0.html; grep -c 'Entreprise partenaire' q0.html
kc update identity-provider/instances/partenaire -r lab -s config.hideOnLoginPage=true
kc get identity-provider/instances/partenaire -r lab | jq -c '{enabled, hideOnLogin: .config.hideOnLoginPage}'
echo "--- masqué, sans hint"
curl -s "http://localhost:8080/realms/lab/protocol/openid-connect/auth?client_id=app-interne&response_type=code&scope=openid&redirect_uri=http://localhost:9999/cb" -o q1.html -w 'HTTP %{http_code}\n'
grep -o 'id="social-[a-z]*"' q1.html; grep -c 'Entreprise partenaire' q1.html; grep -c 'kc-social-providers' q1.html
echo "--- masqué, avec hint"
bash login.sh bruno Bruno-lab-2026 2>&1 | head -6
echo "--- connexion complète avec hint, retour appli ?"
bash login.sh bruno Bruno-lab-2026 2>&1 | grep -o 'RETOUR APPLI: [^?]*'
