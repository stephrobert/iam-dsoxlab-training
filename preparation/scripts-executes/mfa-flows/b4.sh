SUB='browser-mfa%20Browser%20-%20Conditional%202FA'
eid() { kcadm get "authentication/flows/$1/executions" -r lab \
  | jq -r --arg p "$2" '.[]|select(.providerId==$p or .displayName==$p)|.id'; }
req() { kcadm update "authentication/flows/$1/executions" -r lab \
  -b "{\"id\":\"$2\",\"requirement\":\"$3\"}"; }

for p in conditional-user-configured conditional-credential; do
  kcadm delete "authentication/executions/$(eid "$SUB" $p)" -r lab
done
kcadm create "authentication/flows/$SUB/executions/execution" -r lab -s provider=conditional-user-role
COND=$(eid "$SUB" conditional-user-role)
kcadm create "authentication/executions/$COND/config" -r lab \
  -b '{"alias":"role-mfa-requis","config":{"condUserRole":"mfa-requis","negate":"false"}}'
req "$SUB" "$COND" REQUIRED

kcadm create "authentication/flows/$SUB/executions/execution" -r lab -s provider=conditional-user-configured
req "$SUB" "$(eid "$SUB" conditional-user-configured)" REQUIRED
for p in auth-otp-form webauthn-authenticator auth-recovery-authn-code-form; do
  req "$SUB" "$(eid "$SUB" $p)" ALTERNATIVE
done
