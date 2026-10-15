. "$(dirname "$0")/common.sh"
SP=https://sp.exemple.fr/metadata
ACS=https://sp.exemple.fr/acs
ev() { kcadm get events -r lab --fields type,error,clientId,details -q "type=$1" | jq -c '.[0]'; }
kcadm create clients -r lab -s clientId=$SP -s protocol=saml -s "redirectUris=[\"$ACS\"]" \
  -s 'attributes."saml.client.signature"=false' \
  -s "attributes.saml_assertion_consumer_url_post=$ACS" \
  -s 'attributes.saml_name_id_format=username'
page() { curl -s -w '\nHTTP %{http_code}\n' "$1" | sed 's/<[^>]*>/ /g' | tr -s ' \n' | grep -iE "sorry|invalid|not found|error|HTTP|sign in" | head -5; }
echo "--- AuthnRequest correcte"
page "$($PY $S/authnrequest.py $SP $ACS)"
echo "--- émetteur inconnu"
page "$($PY $S/authnrequest.py https://autre.exemple.fr/metadata $ACS)"
ev LOGIN_ERROR
echo "--- ACS non enregistrée"
page "$($PY $S/authnrequest.py $SP https://sp.exemple.fr/autre-acs)"
ev LOGIN_ERROR
docker logs keycloak 2>&1 | grep -E 'client_not_found|invalid_redirect_uri' | grep -E 'sp.exemple|autre' | tail -3
echo "--- métadonnées IdP"
curl -s http://localhost:8080/realms/lab/protocol/saml/descriptor | head -c 600; echo
