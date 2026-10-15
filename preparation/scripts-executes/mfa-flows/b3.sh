kcadm create authentication/flows/browser/copy -r lab -s newName=browser-mfa
kcadm get authentication/flows/browser-mfa/executions -r lab \
  | jq -r '.[]|[.level,.requirement,.displayName]|@tsv'
