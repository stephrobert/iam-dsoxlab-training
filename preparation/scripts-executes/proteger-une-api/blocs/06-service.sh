SAV=$(kcadm create clients -r lab -s clientId=sauvegarde -s publicClient=false \
  -s serviceAccountsEnabled=true -s standardFlowEnabled=false -i)
LEC=$(kcadm get client-scopes -r lab --fields id,name --format csv --noquotes \
  | grep ',notes:lecture$' | cut -d, -f1)
kcadm update "clients/$SAV/default-client-scopes/$LEC" -r lab

( umask 077; kcadm get "clients/$SAV/client-secret" -r lab \
    | jq -r .value | tr -d '\n' > secret-sauvegarde.txt )
ls -l secret-sauvegarde.txt

REP=$(curl -s -X POST "$KC/token" -d grant_type=client_credentials \
  -d client_id=sauvegarde --data-urlencode "client_secret@secret-sauvegarde.txt")
jq 'del(.access_token)' <<<"$REP"
SERVICE=$(jq -r .access_token <<<"$REP")
dec "$SERVICE" | jq -c '{aud, azp, scope, preferred_username, ttl: (.exp - .iat)}'
appel "$API" -H "Authorization: Bearer $SERVICE"
appel -X POST "$API" -H "Authorization: Bearer $SERVICE"
