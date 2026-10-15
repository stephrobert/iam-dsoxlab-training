kcadm() { docker exec kc-lab3 /opt/keycloak/bin/kcadm.sh "$@"; }
eid() { kcadm get "authentication/flows/$1/executions" -r lab | jq -r --arg p "$2" '.[]|select(.providerId==$p or .displayName==$p)|.id'; }
ID=$(eid browser-mfa%20forms mfa-enrolement)
kcadm create authentication/executions/$ID/lower-priority -r lab -b '{}'; echo "2e lower rc=$?"
kcadm get authentication/flows/browser-mfa%20forms/executions -r lab | jq -r '.[]|[.index,.requirement,.displayName]|@tsv' | head -3
echo "## BLOC 9"; 
kcadm update realms/lab -s webAuthnPolicyRpEntityName='Lab IAM' \
  -s webAuthnPolicyUserVerificationRequirement=required \
  -s webAuthnPolicyAttestationConveyancePreference=none
kcadm get realms/lab | jq 'with_entries(select(.key|test("^webAuthnPolicy(RpEntityName|UserVerification|Attestation)")))'
echo "## serverinfo"
TOK=$(curl -s -d client_id=admin-cli -d username=admin -d password=admin -d grant_type=password http://localhost:8093/realms/master/protocol/openid-connect/token | jq -r .access_token)
curl -s -H "Authorization: Bearer $TOK" http://localhost:8093/admin/serverinfo | jq -c '.features[]|select(.name=="PASSKEYS" or .name=="RECOVERY_CODES")'
echo "## required actions"; kcadm get authentication/required-actions -r lab | jq -r '.[]|select(.alias|test("webauthn|RECOVERY"))|[.alias,.enabled]|@tsv'
echo "## BLOC 10"
AID=$(kcadm get users -r lab -q username=alice --fields id --format csv --noquotes)
kcadm get users/$AID/credentials -r lab | jq -r '.[]|[.id,.type,.userLabel]|@tsv'
OTPID=$(kcadm get users/$AID/credentials -r lab | jq -r '.[]|select(.type=="otp")|.id')
kcadm delete users/$AID/credentials/$OTPID -r lab; echo rc=$?
kcadm get users/$AID/credentials -r lab | jq -r '.[]|[.type]|@tsv'
echo "## master"; kcadm get realms/master --fields browserFlow
echo "## config-description"; kcadm get authentication/config-description/conditional-user-role -r lab | jq -c '.properties[]|.name'
echo "## flow 8: URL"; cat b8.sh | tail -1 | head -c 0
