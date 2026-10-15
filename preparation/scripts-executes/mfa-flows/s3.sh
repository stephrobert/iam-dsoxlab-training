kcadm() { docker exec kc-lab3 /opt/keycloak/bin/kcadm.sh "$@"; }
SUB='browser-mfa%20Browser%20-%20Conditional%202FA'
ID=$(kcadm get "authentication/flows/$SUB/executions" -r lab | jq -r '.[]|select(.providerId=="conditional-user-configured")|.id')
kcadm delete "authentication/executions/$ID" -r lab
kcadm get authentication/flows/browser-mfa/executions -r lab | jq -r '.[]|select(.level>=1)|[.level,.requirement,.displayName]|@tsv' | tail -6
python3 p2.py
kcadm get events -r lab -q type=LOGIN_ERROR --fields type,error,userId,details
docker logs kc-lab3 2>&1 | grep -i "LOGIN_ERROR" | tail -2 | cut -c1-500
