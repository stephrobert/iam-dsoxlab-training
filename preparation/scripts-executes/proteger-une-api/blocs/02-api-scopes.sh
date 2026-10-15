# L'API est un client Keycloak sans aucun flow : son identifiant sert d'audience
kcadm create clients -r lab -s clientId=notes-api \
  -s publicClient=false -s standardFlowEnabled=false

# Un client scope par permission, couplé à l'audience de l'API
for scope in notes:lecture notes:ecriture; do
  SID=$(kcadm create client-scopes -r lab -s "name=$scope" -s protocol=openid-connect \
    -s 'attributes."include.in.token.scope"=true' -i)
  kcadm create "client-scopes/$SID/protocol-mappers/models" -r lab \
    -s name=audience-notes-api -s protocol=openid-connect \
    -s protocolMapper=oidc-audience-mapper \
    -s 'config."included.client.audience"=notes-api' \
    -s 'config."access.token.claim"=true' -s 'config."id.token.claim"=false'
done

# Un client public de test : les scopes sont demandés à la carte (optional)
CLI=$(kcadm create clients -r lab -s clientId=notes-cli -s publicClient=true \
  -s standardFlowEnabled=false -s directAccessGrantsEnabled=true -i)
for scope in notes:lecture notes:ecriture; do
  SID=$(kcadm get client-scopes -r lab --fields id,name --format csv --noquotes \
    | grep ",$scope\$" | cut -d, -f1)
  kcadm update "clients/$CLI/optional-client-scopes/$SID" -r lab
done
