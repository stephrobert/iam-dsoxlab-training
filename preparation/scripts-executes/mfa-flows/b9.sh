kcadm update realms/lab -s webAuthnPolicyRpEntityName='Lab IAM' \
  -s webAuthnPolicyUserVerificationRequirement=required \
  -s webAuthnPolicyAttestationConveyancePreference=none
kcadm get realms/lab | jq 'with_entries(select(.key|test("^webAuthnPolicy(RpEntityName|UserVerification|Attestation)")))'
