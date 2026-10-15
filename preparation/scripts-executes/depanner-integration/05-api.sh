. "$(dirname "$0")/common.sh"
cd $S
API=http://127.0.0.1:8090/notes
appel() { curl -s -i "$@" | grep -E '^HTTP|^WWW-Authenticate|^\{'; }
start() { [ -f api.pid ] && kill $(cat api.pid) 2>/dev/null; while ss -ltn | grep -q ":8090 "; do sleep 0.3; done; env "$@" $PY api.py >api.log 2>&1 </dev/null & echo $! > api.pid; until ss -ltn | grep -q ":8090 "; do sleep 0.3; done; }
alice() { curl -s -X POST "$1/protocol/openid-connect/token" -d grant_type=password -d client_id=notes-cli -d username=alice -d password='Alice-lab-2026' -d scope=notes:lecture | jq -r .access_token; }

echo "=== API correcte"
start ISSUER=http://localhost:8080/realms/lab AUDIENCE=notes-api
T=$(alice http://localhost:8080/realms/lab)
appel $API -H "Authorization: Bearer $T"

echo "=== 2. issuer : jeton obtenu via 127.0.0.1"
T2=$(alice http://127.0.0.1:8080/realms/lab)
dec "$T2" | jq -c '{iss, aud}'
appel $API -H "Authorization: Bearer $T2"
echo "--- discovery"
curl -s http://127.0.0.1:8080/realms/lab/.well-known/openid-configuration | jq -r '.issuer, .jwks_uri'
curl -s http://localhost:8080/realms/lab/.well-known/openid-configuration | jq -r '.issuer, .jwks_uri'
echo "--- API configurée sur https"
start ISSUER=https://localhost:8080/realms/lab AUDIENCE=notes-api
appel $API -H "Authorization: Bearer $T"
echo "--- API configurée sur autre realm (master)"
start ISSUER=http://localhost:8080/realms/master AUDIENCE=notes-api
appel $API -H "Authorization: Bearer $T"
echo "--- API configurée sur realm lab2 inexistant"
start ISSUER=http://localhost:8080/realms/lab2 AUDIENCE=notes-api
appel $API -H "Authorization: Bearer $T"
tail -3 api.log

echo "=== 3. audience"
start ISSUER=http://localhost:8080/realms/lab AUDIENCE=notes-api
TS=$(curl -s -X POST $KC/token -d grant_type=password -d client_id=notes-cli -d username=alice -d password='Alice-lab-2026' | jq -r .access_token)
dec "$TS" | jq -c '{iss, aud, scope}'
appel $API -H "Authorization: Bearer $TS"

echo "=== 4. horloge"
dec "$T" | jq -c '{iat, exp, ttl: (.exp-.iat)}'; date +%s
for off in 0 120 301 -30 -600; do
  start ISSUER=http://localhost:8080/realms/lab AUDIENCE=notes-api HORLOGE_DECALAGE=$off
  echo "decalage $off s :"; appel $API -H "Authorization: Bearer $T"
done
kill $(cat api.pid)
