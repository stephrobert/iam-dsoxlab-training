source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-mfa/env.sh
FORMS='browser-mfa%20forms'
SUB='browser-mfa%20Browser%20-%20Conditional%202FA'
ENR='mfa-enrolement'
eid() { kcadm get "authentication/flows/$1/executions" -r lab | jq -r --arg p "$2" '.[]|select(.providerId==$p or .displayName==$p)|.id'; }
req() { kcadm update "authentication/flows/$1/executions" -r lab -b "{\"id\":\"$2\",\"requirement\":\"$3\"}"; }
# sous-flow 1 : condition de configuration restaurée, facteurs au choix
kcadm create "authentication/flows/$SUB/executions/execution" -r lab -s provider=conditional-user-configured
req "$SUB" "$(eid "$SUB" conditional-user-configured)" REQUIRED
for p in auth-otp-form webauthn-authenticator auth-recovery-authn-code-form; do req "$SUB" "$(eid "$SUB" $p)" ALTERNATIVE; done
# sous-flow 2 : enrôlement forcé pour qui n'a encore aucun facteur
kcadm create "authentication/flows/$FORMS/executions/flow" -r lab \
  -s alias=$ENR -s type=basic-flow -s description='Enrolement du premier facteur'
req "$FORMS" "$(eid "$FORMS" $ENR)" CONDITIONAL
kcadm create "authentication/flows/$ENR/executions/execution" -r lab -s provider=conditional-user-role
CR=$(eid $ENR conditional-user-role)
kcadm create "authentication/executions/$CR/config" -r lab -b '{"alias":"role-mfa-requis-enrolement","config":{"condUserRole":"mfa-requis","negate":"false"}}'
req $ENR "$CR" REQUIRED
kcadm create "authentication/flows/$ENR/executions/execution" -r lab -s provider=conditional-sub-flow-executed
CS=$(eid $ENR conditional-sub-flow-executed)
kcadm create "authentication/executions/$CS/config" -r lab -b '{"alias":"sous-flow-2fa-non-execute","config":{"flow_to_check":"browser-mfa Browser - Conditional 2FA","check_result":"not-executed"}}'
req $ENR "$CS" REQUIRED
kcadm create "authentication/flows/$ENR/executions/execution" -r lab -s provider=auth-otp-form
req $ENR "$(eid $ENR auth-otp-form)" REQUIRED
kcadm get authentication/flows/browser-mfa/executions -r lab | jq -r '.[]|select(.displayName|test("forms|Conditional 2FA|enrolement|Condition|OTP|WebAuthn|Recovery|Username"))|[.level,.requirement,.displayName]|@tsv'
