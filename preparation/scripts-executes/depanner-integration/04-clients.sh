. "$(dirname "$0")/common.sh"
ev() { kcadm get events -r lab --fields type,error,clientId,details -q "type=$1" | jq -c '.[0]'; }
echo "--- client_id inconnu"
curl -s -X POST $KC/token -d grant_type=password -d client_id=inconnu -d username=alice -d password='Alice-lab-2026' | jq -c .
ev LOGIN_ERROR
echo "--- client public + secret (password grant)"
curl -s -X POST $KC/token -d grant_type=password -d client_id=notes-cli -d client_secret=unsecret -d username=alice -d password='Alice-lab-2026' | jq -c 'del(.access_token,.refresh_token)'
echo "--- client public, client_credentials"
curl -s -X POST $KC/token -d grant_type=client_credentials -d client_id=notes-cli | jq -c .
ev CLIENT_LOGIN_ERROR
echo "--- confidentiel sans service account, client_credentials, bon secret"
curl -s -X POST $KC/token -d grant_type=client_credentials -d client_id=boutique --data-urlencode client_secret@$S/.boutique-secret | jq -c .
ev CLIENT_LOGIN_ERROR
echo "--- confidentiel, client_credentials, mauvais secret (service account activé)"
BID=$(kcadm get clients -r lab -q clientId=boutique --fields id --format csv --noquotes)
kcadm update clients/$BID -r lab -s serviceAccountsEnabled=true
curl -s -X POST $KC/token -d grant_type=client_credentials -d client_id=boutique -d client_secret=faux | jq -c .
ev CLIENT_LOGIN_ERROR
echo "--- Basic auth faux secret"
curl -s -u boutique:faux -X POST $KC/token -d grant_type=client_credentials | jq -c .
echo "--- password grant, confidentiel, sans secret"
curl -s -X POST $KC/token -d grant_type=password -d client_id=boutique -d username=alice -d password='Alice-lab-2026' | jq -c .
echo "--- password grant désactivé"
curl -s -X POST $KC/token -d grant_type=password -d client_id=boutique --data-urlencode client_secret@$S/.boutique-secret -d username=alice -d password='Alice-lab-2026' | jq -c .
ev LOGIN_ERROR
echo "--- mauvais mot de passe user"
curl -s -X POST $KC/token -d grant_type=password -d client_id=notes-cli -d username=alice -d password='faux' | jq -c .
ev LOGIN_ERROR
