kcadm() { docker exec kc-lab3 /opt/keycloak/bin/kcadm.sh "$@"; }
kcadm update events/config -r lab -s eventsEnabled=true -s 'eventsListeners=["jboss-logging"]'
SUB='browser-mfa%20Browser%20-%20Conditional%202FA'
kcadm get authentication/flows/browser-mfa/executions -r lab | jq -r '.[]|select(.level>=1)|[.level,.requirement,.displayName]|@tsv' | tail -8
python3 p2.py
kcadm get events -r lab -q type=LOGIN_ERROR --fields type,error,userId,details | head -30
docker logs kc-lab3 2>&1 | grep -i "LOGIN_ERROR" | tail -3 | cut -c1-400
