. "$(dirname "$0")/common.sh"
AUTH=$KC/auth
BID=$(kcadm get clients -r lab -q clientId=boutique --fields id --format csv --noquotes)
BSEC=$(kcadm get clients/$BID/client-secret -r lab | jq -r .value)
( umask 077; printf %s "$BSEC" > $S/.boutique-secret )

# connexion par formulaire -> code
getcode() {
  local J=$S/cj.txt; : > $J
  local page; page=$(curl -s -c $J -b $J "$AUTH?client_id=boutique&response_type=code&scope=openid&redirect_uri=http://localhost:3000/callback")
  local act; act=$(grep -o 'action="[^"]*"' <<<"$page" | head -1 | sed 's/action="//;s/"$//;s/&amp;/\&/g')
  curl -s -c $J -b $J -o /dev/null -D - "$act" -d username=alice --data-urlencode password='Alice-lab-2026' | grep -i '^location' | sed 's/.*code=//;s/[& ].*//;s/\r//'
}
tok() { curl -s -X POST $KC/token -d grant_type=authorization_code -d client_id=boutique -d redirect_uri=http://localhost:3000/callback "$@"; }
echo "--- secret faux"
C=$(getcode); echo "code: ${C:0:12}..."
tok -d code=$C -d client_secret=mauvais-secret | jq -c .
echo "--- événement"
kcadm get events -r lab -q type=CODE_TO_TOKEN_ERROR --fields type,error,clientId,details | jq -c '.[0]'
echo "--- bon secret (le code précédent est-il perdu ?)"
tok -d code=$C --data-urlencode client_secret@$S/.boutique-secret | jq -c .
C=$(getcode)
echo "--- bon secret, nouveau code"
R=$(tok -d code=$C --data-urlencode client_secret@$S/.boutique-secret); jq -c 'del(.access_token,.refresh_token,.id_token)' <<<"$R"
echo "--- rejeu du même code"
tok -d code=$C --data-urlencode client_secret@$S/.boutique-secret | jq -c .
kcadm get events -r lab -q type=CODE_TO_TOKEN_ERROR --fields type,error,clientId,details | jq -c '.[0]'
echo "--- redirect_uri différent au token endpoint"
C=$(getcode)
curl -s -X POST $KC/token -d grant_type=authorization_code -d client_id=boutique -d redirect_uri=http://localhost:3000/autre -d code=$C --data-urlencode client_secret@$S/.boutique-secret | jq -c .
kcadm get events -r lab -q type=CODE_TO_TOKEN_ERROR --fields type,error,clientId,details | jq -c '.[0]'
echo "--- sans secret du tout"
C=$(getcode)
tok -d code=$C | jq -c .
kcadm get events -r lab -q type=CODE_TO_TOKEN_ERROR --fields type,error,clientId,details | jq -c '.[0]'
docker logs keycloak 2>&1 | grep -E "CODE_TO_TOKEN_ERROR" | tail -2
