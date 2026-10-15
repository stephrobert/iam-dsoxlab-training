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

echo '### BLOC 6 : parcours du premier login (curl + cookies)'
LAB=http://localhost:8080/realms/lab/protocol/openid-connect
connexion() {   # $1 = utilisateur partenaire, $2 = mot de passe
  local jar; jar=$(mktemp)
  local auth="$LAB/auth?client_id=app-interne&response_type=code&scope=openid&redirect_uri=http://localhost:9999/cb&kc_idp_hint=partenaire"
  local form
  form=$(curl -sL -c "$jar" -b "$jar" "$auth" | grep -o 'action="[^"]*"' | head -1 \
    | sed 's/action="//; s/"$//; s/&amp;/\&/g')
  curl -sL -c "$jar" -b "$jar" --data-urlencode "username=$1" --data-urlencode "password=$2" \
    -w '\nURL finale : %{url_effective}\n' "$form"
}
connexion bruno 'Bruno-lab-2026' | tail -1 | sed 's/code=[^&]*/code=.../; s/session_state=[^&]*/session_state=.../'

echo '### BLOC 7 : vérification du compte importé'
kc get users -r lab -q email=bruno.leroy@partenaire.fr \
  | jq -c '.[] | {username, email, emailVerified, firstName, lastName}'
BID=$(kc get users -r lab -q username=bruno --fields id --format csv --noquotes)
kc get "users/$BID/federated-identity" -r lab | jq -c '.[] | {identityProvider, userName}'
kc get "users/$BID/groups" -r lab | jq -c '.[] | .path'
kc get "users/$BID/role-mappings/realm/composite" -r lab | jq -c '[.[].name]'
kc get "users/$BID/role-mappings" -r lab | jq -c '.clientMappings // {}'

echo '### BLOC 8 : e-mail déjà connu (carole)'
kcp create users -r partenaire -s username=carole -s enabled=true \
  -s firstName=Carole -s lastName=Petit -s email=alice@exemple.fr -s emailVerified=false
kcp set-password -r partenaire --username carole --new-password 'Carole-lab-2026'
connexion carole 'Carole-lab-2026' | grep -o 'kc-feedback-text">[^<]*'
connexion carole 'Carole-lab-2026' | grep -o 'name="submitAction"[^>]*value="[A-Za-z]*"' | sed 's/.*value=/bouton /'
AID=$(kc get users -r lab -q username=alice --fields id --format csv --noquotes)
kc get "users/$AID/federated-identity" -r lab

echo '### BLOC 9 : contre-exemple, lien automatique'
kc create authentication/flows -r lab -s alias=lien-automatique \
  -s providerId=basic-flow -s topLevel=true -s builtIn=false
for P in idp-create-user-if-unique idp-auto-link; do
  kc create authentication/flows/lien-automatique/executions/execution -r lab -s provider=$P
done
for ID in $(kc get authentication/flows/lien-automatique/executions -r lab | jq -r '.[].id'); do
  kc update authentication/flows/lien-automatique/executions -r lab \
    -b "{\"id\":\"$ID\",\"requirement\":\"ALTERNATIVE\"}"
done
kc update identity-provider/instances/partenaire -r lab -s firstBrokerLoginFlowAlias=lien-automatique
RES=$(connexion carole 'Carole-lab-2026' | tail -1)
echo "$RES" | sed 's/code=[^&]*/code=.../; s/session_state=[^&]*/session_state=.../'
CODE=$(sed 's/.*[?&]code=\([^&]*\).*/\1/' <<<"$RES")
curl -s -X POST "$LAB/token" -d grant_type=authorization_code -d client_id=app-interne \
  -d code="$CODE" -d redirect_uri=http://localhost:9999/cb \
  | jq -r .id_token | cut -d. -f2 | tr '_-' '/+' \
  | { read -r s; while [ $(( ${#s} % 4 )) -ne 0 ]; do s="$s="; done; base64 -d <<<"$s"; } \
  | jq -c '{iss, preferred_username, email, email_verified}'
kc get "users/$AID/federated-identity" -r lab | jq -c '.[] | {identityProvider, userName}'

echo '### BLOC 10 : retour au flux par défaut'
kc update identity-provider/instances/partenaire -r lab -s 'firstBrokerLoginFlowAlias=first broker login'
kc get identity-provider/instances/partenaire -r lab | jq -c '{firstBrokerLoginFlowAlias}'

echo '### BLOC 11 : nettoyage'
# docker rm -f keycloak keycloak-partenaire (page)
