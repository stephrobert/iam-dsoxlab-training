kcadm create clients -r lab -s clientId=appli-test -s publicClient=true \
  -s standardFlowEnabled=true -s 'redirectUris=["http://localhost:9999/*"]'
echo "http://localhost:8080/realms/lab/protocol/openid-connect/auth?client_id=appli-test&response_type=code&scope=openid&redirect_uri=http://localhost:9999/cb"
