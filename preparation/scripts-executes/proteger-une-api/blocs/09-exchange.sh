PAS=$(kcadm create clients -r lab -s clientId=passerelle -s publicClient=false \
  -s standardFlowEnabled=false -s directAccessGrantsEnabled=true \
  -s 'attributes."standard.token.exchange.enabled"=true' -i)
kcadm update "clients/$PAS/optional-client-scopes/$LEC" -r lab
PAS_SECRET=$(kcadm get "clients/$PAS/client-secret" -r lab | jq -r .value)

SUJET=$(curl -s -X POST "$KC/token" -d grant_type=password -d client_id=passerelle \
  -d client_secret="$PAS_SECRET" -d username=alice -d password='Alice-lab-2026' \
  | jq -r .access_token)
dec "$SUJET" | jq -c '{aud, azp, scope}'

echanger() {
  curl -s -X POST "$KC/token" -d grant_type=urn:ietf:params:oauth:grant-type:token-exchange \
    -d client_id=passerelle -d client_secret="$PAS_SECRET" -d subject_token="$SUJET" \
    -d subject_token_type=urn:ietf:params:oauth:token-type:access_token \
    -d requested_token_type=urn:ietf:params:oauth:token-type:access_token "$@"
}
REP=$(echanger -d audience=notes-api -d scope=notes:lecture)
jq -c 'del(.access_token)' <<<"$REP"
ECHANGE=$(jq -r .access_token <<<"$REP")
dec "$ECHANGE" | jq -c '{aud, azp, scope, sub, preferred_username}'
appel "$API" -H "Authorization: Bearer $ECHANGE"
echanger -d audience=notes-api | jq -c .
