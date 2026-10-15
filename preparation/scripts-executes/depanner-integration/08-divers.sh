. "$(dirname "$0")/common.sh"
echo "--- codes HTTP du token endpoint"
curl -s -o /dev/null -w 'secret faux: %{http_code}\n' -X POST $KC/token -d grant_type=client_credentials -d client_id=boutique -d client_secret=faux
curl -s -o /dev/null -w 'client inconnu: %{http_code}\n' -X POST $KC/token -d grant_type=client_credentials -d client_id=inconnu -d client_secret=faux
echo "--- /auth client inconnu"
curl -s -w '\nHTTP %{http_code}\n' "$KC/auth?client_id=inconnu&response_type=code&redirect_uri=http://localhost:3000/callback" | sed 's/<[^>]*>/ /g' | tr -s ' \n' | grep -iE "sorry|not found|HTTP"
kcadm get events -r lab -q type=LOGIN_ERROR --fields error,clientId | jq -c '.[0]'
echo "--- en-tête Date de Keycloak"
curl -sI http://localhost:8080/realms/lab | grep -i '^date'; date -u
echo "--- tolérance (leeway) avec horloge -30 s"
cat > $S/leeway.py <<'PY'
import datetime as dt, sys, jwt, jwt.api_jwt as api
class H(dt.datetime):
    @classmethod
    def now(cls, tz=None): return super().now(tz) + dt.timedelta(seconds=-30)
api.datetime = H
t = sys.argv[1]
k = jwt.PyJWKClient("http://localhost:8080/realms/lab/protocol/openid-connect/certs").get_signing_key_from_jwt(t)
for lw in (0, 60):
    try:
        jwt.decode(t, k.key, algorithms=["RS256"], audience="notes-api", leeway=lw); print("leeway", lw, ": accepté")
    except jwt.PyJWTError as e: print("leeway", lw, ":", e)
PY
T=$(curl -s -X POST $KC/token -d grant_type=password -d client_id=notes-cli -d username=alice -d password='Alice-lab-2026' -d scope=notes:lecture | jq -r .access_token)
$PY $S/leeway.py "$T"
echo "--- recherche d'événements filtrée"
kcadm get events -r lab -q client=boutique -q type=CODE_TO_TOKEN_ERROR --fields error | jq -c '.[]' | sort | uniq -c
kcadm get events --help 2>&1 | head -30
