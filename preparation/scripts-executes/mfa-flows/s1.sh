echo '##### BLOC 1'
docker run -d --name kc-lab3 -p 8093:8080 \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \
  -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:26.7.0@sha256:0f198be292568439d700cdbfb893e69a6009bb43a94a06a945b1d3d506c76b13 \
  start-dev
until curl -sf http://localhost:8093/realms/master >/dev/null; do sleep 2; done

kcadm() { docker exec kc-lab3 /opt/keycloak/bin/kcadm.sh "$@"; }
kcadm config credentials --server http://localhost:8080 --realm master --user admin --password admin
kcadm create realms -s realm=lab -s enabled=true
kcadm create groups -r lab -s name=devops
kcadm create groups -r lab -s name=lecteurs
kcadm create roles -r lab -s name=mfa-requis -s 'description=Second facteur obligatoire'
kcadm add-roles -r lab --gname devops --rolename mfa-requis

for u in alice:devops bruno:lecteurs; do
  n=${u%%:*}; g=${u##*:}
  kcadm create users -r lab -s username=$n -s enabled=true \
    -s firstName=$n -s lastName=Lab -s email=$n@exemple.fr
  kcadm set-password -r lab --username $n --new-password 'phrase-de-passe-longue-2026'
  GID=$(kcadm get groups -r lab -q search=$g --fields id --format csv --noquotes)
  UID_=$(kcadm get users -r lab -q username=$n --fields id --format csv --noquotes)
  kcadm update users/$UID_/groups/$GID -r lab \
    -s realm=lab -s userId=$UID_ -s groupId=$GID -n
done
echo '##### BLOC 2'
kcadm update realms/lab -s 'passwordPolicy=length(15) and notUsername'
kcadm get realms/lab --fields passwordPolicy
kcadm set-password -r lab --username bruno --new-password 'Ab1!court'
kcadm set-password -r lab --username bruno --new-password 'abcdefghijklmnopqrstuvwxyz'
kcadm set-password -r lab --username bruno --new-password "$(python3 -c 'print("a-b"*30)')"
kcadm set-password -r lab --username bruno --new-password 'phrase-de-passe-longue-2026'
echo '##### BLOC 3'
kcadm create authentication/flows/browser/copy -r lab -s newName=browser-mfa
kcadm get authentication/flows/browser-mfa/executions -r lab \
  | jq -r '.[]|[.level,.requirement,.displayName]|@tsv'
echo '##### BLOC 4'
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
echo '##### BLOC 7'
kcadm update realms/lab -s browserFlow=browser-mfa
kcadm get realms/lab --fields browserFlow
echo '##### BLOC 8 (sans echo)'
kcadm create clients -r lab -s clientId=appli-test -s publicClient=true \
  -s standardFlowEnabled=true -s 'redirectUris=["http://localhost:9999/*"]'
kcadm get users/$(kcadm get users -r lab -q username=alice --fields id --format csv --noquotes)/groups -r lab --fields name
