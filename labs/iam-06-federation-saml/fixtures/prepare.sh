#!/usr/bin/env bash
# Pose la situation du lab iam-06, et la retire avec `--nettoyer`.
#
# LE FOURNISSEUR DE SERVICE TÉMOIN EST UN SECOND REALM DU MÊME KEYCLOAK
#
# Le choix est délibéré, et il tient à trois raisons :
#
#   - aucune dépendance nouvelle : c'est l'image du socle, déjà épinglée par
#     digest et maintenue, là où les fournisseurs de service SAML en conteneur
#     sont rares et mal entretenus ;
#   - reproductible : rien à télécharger, rien qui puisse disparaître d'un
#     registre entre deux sessions de formation ;
#   - pédagogiquement juste : Keycloak sait jouer les DEUX rôles, et le lab
#     montre donc les deux côtés de SAML, celui qui émet l'assertion et celui
#     qui la consomme. C'est précisément la distinction que le protocole impose.
#
# CE QUE CE SCRIPT NE FAIT PAS : le client SAML côté émetteur, ni le
# fournisseur d'identité côté consommateur. C'est le travail demandé, des deux
# côtés.
#
# La trace va dans /var/log/dsoxlab-prepare.log, avec `set -x`, interrompue
# autour de chaque secret : ce journal est collecté par `dsoxlab support`.
set -euo pipefail

JOURNAL=/var/log/dsoxlab-prepare.log
exec > >(tee -a "$JOURNAL") 2>&1
set -x

KC=http://127.0.0.1:8080
IDP_REALM=formation
SP_REALM=partenaire-sp
SOCLE_ENV=/opt/socle-iam/.env
IDENTIFIANTS=/opt/iam-lab/identifiants-lab.txt
APPLI=/opt/iam-lab/appli-temoin
PORT_TEMOIN=9080

if [ ! -r "$SOCLE_ENV" ]; then
  echo "ÉCHEC : $SOCLE_ENV est absent ou illisible. Le socle IAM n'est pas" >&2
  echo "installé, ou ce script tourne sous un compte hors du groupe docker." >&2
  exit 1
fi

set +x
KC_USER=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME=' "$SOCLE_ENV" | cut -d= -f2-)
KC_MDP=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD=' "$SOCLE_ENV" | cut -d= -f2-)
JETON=$(curl -sS --max-time 20 -X POST \
  "$KC/realms/master/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  -d "username=$KC_USER" -d "password=$KC_MDP" \
  | jq -r '.access_token // empty')
# Le test qui suit reste dans la zone NON tracée : `set -x` journaliserait
# la valeur du jeton, et ce fichier est collecté par `dsoxlab support`.
if [ -z "$JETON" ]; then
  echo "ÉCHEC : aucun jeton d'administration. Keycloak répond-il sur $KC ?" >&2
  exit 1
fi
set -x

admin() { # $1 méthode, $2 chemin sous /admin, $3 corps
  set +x
  local m=$1 c=$2 b=${3:-}
  if [ -n "$b" ]; then
    curl -sS --max-time 30 -X "$m" "$KC/admin/$c" \
      -H "Authorization: Bearer $JETON" -H 'Content-Type: application/json' -d "$b"
  else
    curl -sS --max-time 30 -X "$m" "$KC/admin/$c" -H "Authorization: Bearer $JETON"
  fi
  set -x
}

# ─── Mode nettoyage, appelé par cleanup.yaml ──────────────────────────────────
if [ "${1:-}" = "--nettoyer" ]; then
  /opt/iam-lab/outils/arreter-temoin.sh "$PORT_TEMOIN" || true
  rm -f "$APPLI/configuration.json" "$APPLI/temoin.log"

  # Retirer le realm du fournisseur de service emporte tout ce qu'il contient :
  # son client, son groupe, son fournisseur d'identité et les comptes liés.
  admin DELETE "realms/$SP_REALM" > /dev/null

  # Côté émetteur, le client SAML que l'apprenant a créé, s'il existe. Son
  # identifiant est l'URL du realm consommateur, qu'il faut encoder.
  ENTITE=$(printf '%s' "$KC/realms/$SP_REALM" | jq -sRr @uri)
  ID_CLIENT=$(admin GET "realms/$IDP_REALM/clients?clientId=$ENTITE" \
    | jq -r '.[0].id // empty')
  [ -n "$ID_CLIENT" ] && admin DELETE "realms/$IDP_REALM/clients/$ID_CLIENT" > /dev/null

  ID_ALICE=$(admin GET "realms/$IDP_REALM/users?username=alice&exact=true" \
    | jq -r '.[0].id // empty')
  [ -n "$ID_ALICE" ] && admin DELETE "realms/$IDP_REALM/users/$ID_ALICE" > /dev/null

  for id in $(admin GET "realms/$IDP_REALM/groups" | jq -r '.[].id'); do
    admin DELETE "realms/$IDP_REALM/groups/$id" > /dev/null
  done

  rm -f "$IDENTIFIANTS"
  echo "nettoyage du lab iam-06 terminé"
  exit 0
fi

# ─── Retirer tout travail d'un passage précédent ──────────────────────────────
# Le realm consommateur est recréé à neuf. C'est plus simple et plus sûr que de
# retirer ses objets un par un : un fournisseur d'identité oublié rendrait vert
# un test qui ne mesure plus le travail de l'apprenant.
/opt/iam-lab/outils/arreter-temoin.sh "$PORT_TEMOIN" || true
rm -f "$APPLI/configuration.json" "$APPLI/temoin.log"
admin DELETE "realms/$SP_REALM" > /dev/null

ENTITE=$(printf '%s' "$KC/realms/$SP_REALM" | jq -sRr @uri)
ID_CLIENT=$(admin GET "realms/$IDP_REALM/clients?clientId=$ENTITE" \
  | jq -r '.[0].id // empty')
[ -n "$ID_CLIENT" ] && admin DELETE "realms/$IDP_REALM/clients/$ID_CLIENT" > /dev/null

ID_ALICE=$(admin GET "realms/$IDP_REALM/users?username=alice&exact=true" \
  | jq -r '.[0].id // empty')
[ -n "$ID_ALICE" ] && admin DELETE "realms/$IDP_REALM/users/$ID_ALICE" > /dev/null
for id in $(admin GET "realms/$IDP_REALM/groups" | jq -r '.[].id'); do
  admin DELETE "realms/$IDP_REALM/groups/$id" > /dev/null
done

# ─── Côté émetteur : un compte et son groupe ──────────────────────────────────
set +x
SECRET_DU_COMPTE=$(openssl rand -hex 12)
set -x

admin POST "realms/$IDP_REALM/users" "$(jq -nc '{
  username:"alice", enabled:true, emailVerified:true,
  firstName:"Aline", lastName:"Dupont", email:"aline@formation.lab"}')" > /dev/null
ID_ALICE=$(admin GET "realms/$IDP_REALM/users?username=alice&exact=true" \
  | jq -r '.[0].id // empty')
if [ -z "$ID_ALICE" ]; then
  echo "ÉCHEC : alice n'existe pas après sa création." >&2
  exit 1
fi
set +x
admin PUT "realms/$IDP_REALM/users/$ID_ALICE/reset-password" \
  "$(jq -nc --arg m "$SECRET_DU_COMPTE" \
     '{type:"password", value:$m, temporary:false}')" > /dev/null
set -x

admin POST "realms/$IDP_REALM/groups" '{"name":"devops"}' > /dev/null
ID_GROUPE=$(admin GET "realms/$IDP_REALM/groups" \
  | jq -r '.[] | select(.name=="devops") | .id')
admin PUT "realms/$IDP_REALM/users/$ID_ALICE/groups/$ID_GROUPE" '{}' > /dev/null

# ─── Côté consommateur : le realm du fournisseur de service, vide ─────────────
admin POST realms "$(jq -nc --arg r "$SP_REALM" '{
  realm:$r, enabled:true, displayName:"Entreprise partenaire"}')" > /dev/null

# Son groupe, qui doit préexister pour qu'un compte y soit rangé : un mappeur de
# groupe ne CRÉE pas le groupe, il y met le compte.
admin POST "realms/$SP_REALM/groups" '{"name":"devops"}' > /dev/null

# Et son client OIDC, par lequel l'application témoin s'y connecte. C'est de
# l'outillage : le sujet du lab est SAML, et il n'y a aucune raison de
# redemander un client OIDC déjà travaillé au lab 04.
admin POST "realms/$SP_REALM/clients" "$(jq -nc '{
  clientId:"appli-notes", name:"Application notes", enabled:true,
  publicClient:true, standardFlowEnabled:true, implicitFlowEnabled:false,
  directAccessGrantsEnabled:false, serviceAccountsEnabled:false,
  redirectUris:["http://127.0.0.1:9080/callback"],
  webOrigins:["http://127.0.0.1:9080"],
  attributes:{"pkce.code.challenge.method":"S256"}}')" > /dev/null

# ─── L'application témoin, pointée sur le CONSOMMATEUR ────────────────────────
# `idp_hint` la fait demander directement le fournisseur d'identité nommé, au
# lieu de la page de connexion du realm consommateur. Sans lui, le parcours
# s'arrête sur un formulaire local où le compte n'existe pas, et le test
# conclurait à tort que la fédération est cassée.
cat > "$APPLI/configuration.json" <<CONF
{
  "issuer": "$KC/realms/$SP_REALM",
  "client_id": "appli-notes",
  "redirect_uri": "http://127.0.0.1:$PORT_TEMOIN/callback",
  "idp_hint": "saml-formation"
}
CONF
chown student:docker "$APPLI/configuration.json"
chmod 0660 "$APPLI/configuration.json"

touch "$APPLI/temoin.log"
chown student:docker "$APPLI/temoin.log"
chmod 0660 "$APPLI/temoin.log"

setsid nohup "$APPLI/.venv/bin/python" "$APPLI/appli.py" \
  > "$APPLI/temoin.log" 2>&1 &
for _ in $(seq 1 30); do
  if curl -sS -o /dev/null --max-time 2 "http://127.0.0.1:$PORT_TEMOIN/etat"; then
    break
  fi
  sleep 1
done
if ! curl -sS -o /dev/null --max-time 5 "http://127.0.0.1:$PORT_TEMOIN/etat"; then
  echo "ÉCHEC : l'application témoin ne répond pas sur le port $PORT_TEMOIN." >&2
  tail -20 "$APPLI/temoin.log" >&2 || true
  exit 1
fi

# ─── Ce que l'apprenant doit savoir pour commencer ────────────────────────────
set +x
{
  echo "# Posé par le setup du lab iam-06. Jetable."
  echo "REALM_EMETTEUR=${IDP_REALM}"
  echo "REALM_CONSOMMATEUR=${SP_REALM}"
  echo "ENTITE_CONSOMMATEUR=${KC}/realms/${SP_REALM}"
  echo "ACS_CONSOMMATEUR=${KC}/realms/${SP_REALM}/broker/saml-formation/endpoint"
  echo "ALIAS_ATTENDU=saml-formation"
  echo "METADONNEES_EMETTEUR=${KC}/realms/${IDP_REALM}/protocol/saml/descriptor"
  echo "UTILISATEUR=alice"
  printf 'MOT_DE_PASSE=%s\n' "$SECRET_DU_COMPTE"
  echo "GROUPE=devops"
} > "$IDENTIFIANTS"
chown student:docker "$IDENTIFIANTS"
chmod 0640 "$IDENTIFIANTS"
set -x

# ─── Contrôler l'état posé ────────────────────────────────────────────────────
# Sur l'ÉTAT, et non sur le code de retour des créations : un realm absent ou un
# compte sans groupe ferait échouer un test de SAML, et l'apprenant chercherait
# la cause dans son assertion.
if [ "$(admin GET "realms/$SP_REALM" | jq -r '.realm // empty')" != "$SP_REALM" ]; then
  echo "ÉCHEC : le realm $SP_REALM n'existe pas après sa création." >&2
  exit 1
fi
if [ "$(admin GET "realms/$IDP_REALM/users/$ID_ALICE/groups" | jq 'length')" -ne 1 ]; then
  echo "ÉCHEC : alice n'est pas dans exactement un groupe côté émetteur." >&2
  exit 1
fi

set +x
echo "Situation posée : realm $SP_REALM vide côté consommateur, compte alice"
echo "et groupe devops côté émetteur, application témoin en service."
echo "Identifiants dans $IDENTIFIANTS"
