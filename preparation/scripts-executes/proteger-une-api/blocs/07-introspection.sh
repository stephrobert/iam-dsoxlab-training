NOTES=$(kcadm get clients -r lab -q clientId=notes-api --fields id --format csv --noquotes)
NOTES_SECRET=$(kcadm get "clients/$NOTES/client-secret" -r lab | jq -r .value)
curl -s -X POST "$KC/token/introspect" -u "notes-api:$NOTES_SECRET" -d token="$AVEC" \
  | jq -c '{active, aud, scope, client_id}'
curl -s -X POST "$KC/token/introspect" -u "notes-api:$NOTES_SECRET" -d token="$SANS" \
  | jq -c .
