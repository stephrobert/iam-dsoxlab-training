#!/usr/bin/env bash
cd "$(dirname "$0")"
kc() { docker exec keycloak /opt/keycloak/bin/kcadm.sh "$@"; }
AID=$(kc get users -r lab -q username=alice --fields id --format csv --noquotes)
GID=$(kc get groups -r lab -q search=partenaires | jq -r '.[0].id')
MID=$(kc get identity-provider/instances/partenaire/mappers -r lab | jq -r '.[]|select(.name=="groupe-partenaires").id')
echo "== remise à zéro"
kc delete "users/$AID/federated-identity/partenaire" -r lab; echo "rc=$?"
kc delete "users/$AID/groups/$GID" -r lab; echo "rc=$?"
kc update identity-provider/instances/partenaire/mappers/$MID -r lab -s config.syncMode=INHERIT
kc get "users/$AID/federated-identity" -r lab; kc get "users/$AID/groups" -r lab
echo "== carole: écran de choix"
bash login.sh carole Carole-lab-2026 2>&1 | tail -1
bash cont.sh submitAction=linkAccount | tail -3
bash cont.sh username=alice password=Alice-lab-2026
kc get "users/$AID/federated-identity" -r lab | jq -c '.[]|{identityProvider,userName}'
echo "groupes: $(kc get "users/$AID/groups" -r lab | jq -c '[.[].path]')"
echo "== reconnexion en IMPORT"
bash login.sh carole Carole-lab-2026 2>&1 | tail -2 | cut -c1-120
echo "groupes: $(kc get "users/$AID/groups" -r lab | jq -c '[.[].path]')"
echo "== FORCE"
kc update identity-provider/instances/partenaire/mappers/$MID -r lab -s config.syncMode=FORCE
bash login.sh carole Carole-lab-2026 2>&1 | tail -2 | cut -c1-120
echo "groupes: $(kc get "users/$AID/groups" -r lab | jq -c '[.[].path]')"
