. "$(dirname "$0")/common.sh"
AUTH=$KC/auth
echo "--- bon redirect_uri"
curl -s -o /dev/null -w '%{http_code}\n' "$AUTH?client_id=boutique&response_type=code&scope=openid&redirect_uri=http://localhost:3000/callback"
echo "--- mauvais redirect_uri (slash final)"
curl -s -w '\nHTTP %{http_code}\n' "$AUTH?client_id=boutique&response_type=code&scope=openid&redirect_uri=http://localhost:3000/callback/" | sed 's/<[^>]*>/ /g' | tr -s ' \n' | grep -iE "sorry|invalid|HTTP"
echo "--- mauvais port"
curl -s -o /dev/null -w 'HTTP %{http_code}\n' "$AUTH?client_id=boutique&response_type=code&scope=openid&redirect_uri=http://localhost:3001/callback"
echo "--- événements"
kcadm get events -r lab --fields type,error,clientId,details --format csv --noquotes 2>&1 | head
kcadm get events -r lab -q type=LOGIN_ERROR 2>&1 | head -40
echo "--- journal"
docker logs keycloak 2>&1 | grep -E "LOGIN_ERROR" | tail -3
