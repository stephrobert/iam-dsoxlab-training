kcadm() { docker exec kc-lab3 /opt/keycloak/bin/kcadm.sh "$@"; }
lst() { kcadm get authentication/flows/browser-mfa%20forms/executions -r lab | jq -r '.[]|[.index,.priority,.requirement,.displayName]|@tsv'; }
kcadm create "authentication/flows/browser-mfa%20forms/executions/flow" -r lab -s alias=tmp-a -s type=basic-flow >/dev/null
lst
echo ---; TID=$(kcadm get authentication/flows/browser-mfa%20forms/executions -r lab | jq -r '.[]|select(.displayName=="tmp-a")|.id')
kcadm create authentication/executions/$TID/raise-priority -r lab -b '{}'; lst
echo ---; kcadm create authentication/executions/$TID/lower-priority -r lab -b '{}'; echo rc=$?; lst
kcadm delete authentication/executions/$TID -r lab
