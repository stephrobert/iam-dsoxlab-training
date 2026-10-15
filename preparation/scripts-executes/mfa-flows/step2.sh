source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-mfa/env.sh
SUB='browser-mfa%20Browser%20-%20Conditional%202FA'
execs() { kcadm get "authentication/flows/$SUB/executions" -r lab; }
# 1. retirer les deux conditions d'origine
for id in $(execs | jq -r '.[]|select(.providerId=="conditional-user-configured" or .providerId=="conditional-credential")|.id'); do
  kcadm delete "authentication/executions/$id" -r lab
done
# 2. ajouter la condition sur le rôle
kcadm create "authentication/flows/$SUB/executions/execution" -r lab -s provider=conditional-user-role
COND=$(execs | jq -r '.[]|select(.providerId=="conditional-user-role")|.id')
kcadm create "authentication/executions/$COND/config" -r lab -b '{"alias":"role-mfa-requis","config":{"condUserRole":"mfa-requis","negate":"false"}}'
# 3. exigences : condition REQUIRED, facteurs ALTERNATIVE
set_req() { # providerId requirement
  local id; id=$(execs | jq -r --arg p "$1" '.[]|select(.providerId==$p)|.id')
  kcadm update "authentication/flows/$SUB/executions" -r lab -b "{\"id\":\"$id\",\"requirement\":\"$2\"}"
}
set_req conditional-user-role REQUIRED
set_req auth-otp-form ALTERNATIVE
set_req webauthn-authenticator ALTERNATIVE
set_req auth-recovery-authn-code-form ALTERNATIVE
execs | jq -r '.[]|[.level,.requirement,.displayName]|@tsv'
