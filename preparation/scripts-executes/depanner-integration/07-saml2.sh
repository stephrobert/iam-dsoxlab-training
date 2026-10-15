. "$(dirname "$0")/common.sh"
SP=https://sp.exemple.fr/metadata
ACS=https://sp.exemple.fr/acs
echo "--- codes HTTP"
for args in "$SP $ACS" "https://autre.exemple.fr/metadata $ACS" "$SP https://sp.exemple.fr/autre-acs"; do
  curl -s -o /dev/null -w '%{http_code}  ' "$($PY $S/authnrequest.py $args)"; echo "$args"
done
echo "--- événements bruts"
kcadm get events -r lab -q type=LOGIN_ERROR --fields time,error,clientId,details | jq -c '.[0:2][]'
echo "--- journal"
docker logs keycloak 2>&1 | grep 'type="LOGIN_ERROR"' | tail -2 | sed 's/realmId="[^"]*", //'
echo "--- connexion SAML complète"
J=$S/cjs.txt; : > $J
U=$($PY $S/authnrequest.py $SP $ACS)
page=$(curl -s -c $J -b $J "$U")
act=$(grep -o 'action="[^"]*"' <<<"$page" | head -1 | sed 's/action="//;s/"$//;s/&amp;/\&/g')
curl -s -c $J -b $J "$act" -d username=alice --data-urlencode password='Alice-lab-2026' > $S/saml-post.html
grep -o '<form[^>]*>' $S/saml-post.html | head -2
grep -o 'name="SAMLResponse"' $S/saml-post.html | head -1
RESP=$(grep -o 'name="SAMLResponse" value="[^"]*"' $S/saml-post.html | sed 's/.*value="//;s/"$//')
echo "$RESP" | base64 -d > $S/saml-response.xml
python3 - <<PY
import re
x=open("$S/saml-response.xml").read()
for tag,pat in [("Destination",r'Destination="([^"]*)"'),("InResponseTo",r'InResponseTo="([^"]*)"'),("Issuer",r'<saml:Issuer>([^<]*)</saml:Issuer>'),("StatusCode",r'<samlp:StatusCode Value="([^"]*)"'),("Audience",r'<saml:Audience>([^<]*)</saml:Audience>'),("NotBefore",r'NotBefore="([^"]*)"'),("NotOnOrAfter",r'NotOnOrAfter="([^"]*)"'),("Recipient",r'Recipient="([^"]*)"'),("NameID",r'<saml:NameID[^>]*>([^<]*)</saml:NameID>'),("Signature",r'(<dsig:Signature|<ds:Signature)')]:
    print(tag, re.findall(pat,x)[:3])
PY
