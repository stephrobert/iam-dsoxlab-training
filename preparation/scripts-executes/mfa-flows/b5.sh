FORMS='browser-mfa%20forms'; ENR='mfa-enrolement'
kcadm create "authentication/flows/$FORMS/executions/flow" -r lab \
  -s alias=$ENR -s type=basic-flow -s description='Enrolement du premier facteur'
req "$FORMS" "$(eid "$FORMS" $ENR)" CONDITIONAL

kcadm create "authentication/flows/$ENR/executions/execution" -r lab -s provider=conditional-user-role
CR=$(eid $ENR conditional-user-role)
kcadm create "authentication/executions/$CR/config" -r lab \
  -b '{"alias":"role-mfa-requis-enrolement","config":{"condUserRole":"mfa-requis","negate":"false"}}'
req $ENR "$CR" REQUIRED

kcadm create "authentication/flows/$ENR/executions/execution" -r lab -s provider=conditional-sub-flow-executed
CS=$(eid $ENR conditional-sub-flow-executed)
kcadm create "authentication/executions/$CS/config" -r lab \
  -b '{"alias":"sous-flow-2fa-non-execute","config":{"flow_to_check":"browser-mfa Browser - Conditional 2FA","check_result":"not-executed"}}'
req $ENR "$CS" REQUIRED

kcadm create "authentication/flows/$ENR/executions/execution" -r lab -s provider=auth-otp-form
req $ENR "$(eid $ENR auth-otp-form)" REQUIRED
