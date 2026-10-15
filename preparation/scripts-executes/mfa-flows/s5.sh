kcadm() { docker exec kc-lab3 /opt/keycloak/bin/kcadm.sh "$@"; }
kcadm create "authentication/flows/browser-mfa%20forms/executions/flow" -r lab -s alias=tmp-ordre -s type=basic-flow
kcadm get authentication/flows/browser-mfa/executions -r lab | jq -r '.[]|select(.displayName|test("forms|Conditional 2FA|tmp-ordre|Username"))|[.level,.index,.requirement,.displayName]|@tsv'
TID=$(kcadm get authentication/flows/browser-mfa%20forms/executions -r lab | jq -r '.[]|select(.displayName=="tmp-ordre")|.id')
kcadm delete authentication/executions/$TID -r lab; echo del rc=$?
kcadm delete authentication/flows/browser -r lab; echo "rc=$?"
BID=$(kcadm get authentication/flows -r lab -q alias=browser --fields id,alias --format csv --noquotes | head -1 | cut -d, -f1)
kcadm delete authentication/flows/$BID -r lab; echo "rc=$?"
