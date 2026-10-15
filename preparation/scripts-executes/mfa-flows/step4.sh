source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-mfa/env.sh
echo "## mots de passe"
kcadm set-password -r lab --username bruno --new-password 'abcdefghijklmnopqrstuvwxyz' && echo "26 minuscules sans chiffre : accepté"
kcadm set-password -r lab --username bruno --new-password "$(python3 -c 'print("a-b"*30)')" && echo "90 caracteres : accepté"
kcadm set-password -r lab --username bruno --new-password 'Ab1!court' ; echo "9 caracteres complexes : refusé (code $?)"
kcadm set-password -r lab --username bruno --new-password 'phrase-de-passe-longue-2026'
echo "## politique WebAuthn"
kcadm update realms/lab -s webAuthnPolicyRpEntityName='Lab IAM' -s webAuthnPolicyUserVerificationRequirement=required -s webAuthnPolicyAttestationConveyancePreference=none
kcadm get realms/lab | jq 'with_entries(select(.key|test("^webAuthnPolicy(RpEntityName|UserVerification|Attestation|SignatureAlg)")))' 
echo "## OTP policy"; kcadm get realms/lab | jq -c '{otpPolicyType,otpPolicyAlgorithm,otpPolicyDigits,otpPolicyPeriod,otpPolicyLookAheadWindow}'
echo "## master"; kcadm get realms/master --fields browserFlow,passwordPolicy
echo "## flow par défaut"; BID=$(kcadm get authentication/flows -r lab -q alias=browser --fields id,alias --format csv --noquotes | head -1 | cut -d, -f1); kcadm delete authentication/flows/$BID -r lab; echo "code $?"
echo "## flows du realm"; kcadm get authentication/flows -r lab --fields alias,builtIn --format csv --noquotes
echo "## required actions 2FA"; kcadm get authentication/required-actions -r lab | jq -r '.[]|select(.alias|test("TOTP|webauthn|RECOVERY"))|[.alias,.name,.enabled]|@tsv'
