kcadm update "clients/$CLI" -r lab \
  -s 'attributes."oauth2.device.authorization.grant.enabled"=true'
DEV=$(curl -s -X POST "$KC/auth/device" -d client_id=notes-cli -d scope=notes:lecture)
jq . <<<"$DEV"
curl -s -X POST "$KC/token" -d grant_type=urn:ietf:params:oauth:grant-type:device_code \
  -d client_id=notes-cli -d device_code="$(jq -r .device_code <<<"$DEV")" | jq -c .
