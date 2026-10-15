ID=$(eid "$FORMS" $ENR)
kcadm create authentication/executions/$ID/lower-priority -r lab -b '{}'
kcadm create authentication/executions/$ID/lower-priority -r lab -b '{}'
kcadm get authentication/flows/browser-mfa/executions -r lab \
  | jq -r '.[]|select(.displayName|test("forms|Conditional 2FA|enrolement|Username"))|[.level,.requirement,.displayName]|@tsv'
