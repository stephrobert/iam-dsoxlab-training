#!/usr/bin/env bash
# Rejeu des blocs de la page, dans l'ordre. Conteneurs supprimés avant.
docker rm -f keycloak keycloak-partenaire >/dev/null 2>&1
set -u

echo '### BLOC 1 : démarrage'
IMG=quay.io/keycloak/keycloak:26.7.0@sha256:0f198be292568439d700cdbfb893e69a6009bb43a94a06a945b1d3d506c76b13
docker run -d --name keycloak --network host \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=admin -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin \
  "$IMG" start-dev
docker run -d --name keycloak-partenaire --network host \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=admin -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin \
  -e KC_HTTP_PORT=8082 \
  "$IMG" start-dev
until curl -sf http://localhost:8080/realms/master >/dev/null; do sleep 2; done
until curl -sf http://localhost:8082/realms/master >/dev/null; do sleep 2; done

echo '### BLOC 2 : partenaire'
kcp() { docker exec keycloak-partenaire /opt/keycloak/bin/kcadm.sh "$@"; }
kcp config credentials --server http://localhost:8082 --realm master --user admin --password admin
kcp create realms -s realm=partenaire -s enabled=true
kcp create users -r partenaire -s username=bruno -s enabled=true \
  -s firstName=Bruno -s lastName=Leroy -s email=bruno.leroy@partenaire.fr -s emailVerified=true
kcp set-password -r partenaire --username bruno --new-password 'Bruno-lab-2026'
CID=$(kcp create clients -r partenaire -s clientId=portail-entreprise \
  -s publicClient=false -s standardFlowEnabled=true \
  -s 'redirectUris=["http://localhost:8080/realms/lab/broker/partenaire/endpoint"]' -i)
SECRET=$(kcp get "clients/$CID/client-secret" -r partenaire | jq -r .value)

echo '### BLOC 3 : realm lab'
kc() { docker exec keycloak /opt/keycloak/bin/kcadm.sh "$@"; }
kc config credentials --server http://localhost:8080 --realm master --user admin --password admin
kc create realms -s realm=lab -s enabled=true
kc create groups -r lab -s name=partenaires
kc create clients -r lab -s clientId=app-interne -s publicClient=true \
  -s standardFlowEnabled=true -s 'redirectUris=["http://localhost:9999/*"]'
kc create users -r lab -s username=alice -s enabled=true \
  -s firstName=Alice -s lastName=Martin -s email=alice@exemple.fr
kc set-password -r lab --username alice --new-password 'Alice-lab-2026'

echo '### BLOC 4 : IdP'
EP=http://localhost:8082/realms/partenaire/protocol/openid-connect
kc create identity-provider/instances -r lab \
  -s alias=partenaire -s providerId=oidc -s enabled=true \
  -s displayName='Entreprise partenaire' -s trustEmail=false \
  -s 'firstBrokerLoginFlowAlias=first broker login' \
  -s config.issuer=http://localhost:8082/realms/partenaire \
  -s config.authorizationUrl=$EP/auth -s config.tokenUrl=$EP/token \
  -s config.jwksUrl=$EP/certs -s config.useJwksUrl=true \
  -s config.validateSignature=true -s config.clientAuthMethod=client_secret_post \
  -s config.clientId=portail-entreprise -s config.clientSecret="$SECRET" \
  -s 'config.defaultScope=openid email profile' -s config.syncMode=IMPORT
kc get identity-provider/instances/partenaire -r lab \
  | jq '{alias, providerId, enabled, trustEmail, firstBrokerLoginFlowAlias, config: (.config | del(.clientSecret))}'

echo '### BLOC 5 : mappers'
M=identity-provider/instances/partenaire/mappers
for PAIRE in email:email given_name:firstName family_name:lastName; do
  CLAIM=${PAIRE%%:*}; ATTR=${PAIRE##*:}
  kc create $M -r lab -s "name=$CLAIM" -s identityProviderAlias=partenaire \
    -s identityProviderMapper=oidc-user-attribute-idp-mapper \
    -s "config.claim=$CLAIM" -s "config.\"user.attribute\"=$ATTR" -s config.syncMode=INHERIT
done
kc create $M -r lab -s name=groupe-partenaires -s identityProviderAlias=partenaire \
  -s identityProviderMapper=oidc-hardcoded-group-idp-mapper \
  -s config.group=/partenaires -s config.syncMode=INHERIT
kc get $M -r lab | jq -c '.[] | {name, identityProviderMapper, config}'

echo '### carole'
kcp create users -r partenaire -s username=carole -s enabled=true \
  -s firstName=Carole -s lastName=Petit -s email=alice@exemple.fr -s emailVerified=false
kcp set-password -r partenaire --username carole --new-password 'Carole-lab-2026'
echo "$SECRET" > /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/lab-federation/secret.txt
