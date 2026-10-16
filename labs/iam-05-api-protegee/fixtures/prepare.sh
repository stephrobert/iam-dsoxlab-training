#!/usr/bin/env bash
# Pose la situation du lab iam-05, et la retire avec `--nettoyer`.
#
# CE QUE CE SCRIPT NE FAIT PAS : déclarer l'API, ses scopes, son audience ni le
# client du service de sauvegarde. C'est le travail demandé.
#
# CE QU'IL POSE, ET QUI EST DE L'OUTILLAGE DE TEST, PAS DU TRAVAIL :
#
#   notes-cli     un client public avec octroi direct, par lequel les tests
#                 obtiennent des jetons. Sans lui, aucun test ne pourrait
#                 appeler l'API, et le lab ne serait pas notable.
#   autre-api     une seconde API, et son scope `autre:lecture` qui porte son
#                 audience. Elle existe pour UNE SEULE RAISON : produire un
#                 jeton parfaitement signé mais destiné à quelqu'un d'autre.
#                 C'est le jeton que l'API de départ accepte, et c'est le coeur
#                 du lab.
#   alice         le compte humain du lab.
#
# La trace va dans /var/log/dsoxlab-prepare.log, avec `set -x`.
set -euo pipefail

JOURNAL=/var/log/dsoxlab-prepare.log
exec > >(tee -a "$JOURNAL") 2>&1
set -x

KC=http://127.0.0.1:8080
REALM=formation
API=/opt/iam-lab/api-notes
PORT_API=8090
IDENTIFIANTS=/opt/iam-lab/identifiants-lab.txt
SECRETS=/opt/socle-iam/secrets.yml

#: Ce que l'apprenant doit créer, et que l'on retire donc entre deux passages.
CLIENTS_DU_TRAVAIL=(notes-api service-sauvegarde)
SCOPES_DU_TRAVAIL=(notes:lecture notes:ecriture)

#: L'outillage de test, posé par ce script.
CLIENTS_OUTILLAGE=(notes-cli autre-api)
SCOPES_OUTILLAGE=(autre:lecture)

if [ ! -r "$SECRETS" ]; then
  echo "ÉCHEC : $SECRETS est absent ou illisible. Le socle IAM n'est pas" >&2
  echo "installé, ou ce script tourne sous un compte hors du groupe docker." >&2
  exit 1
fi

jeton_admin() {
  local utilisateur mot_de_passe jeton
  utilisateur=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME:' "$SECRETS" | cut -d'"' -f2)
  mot_de_passe=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD:' "$SECRETS" | cut -d'"' -f2)
  jeton=$(curl -sS --max-time 20 -X POST \
    "$KC/realms/master/protocol/openid-connect/token" \
    -d grant_type=password -d client_id=admin-cli \
    -d "username=$utilisateur" -d "password=$mot_de_passe" \
    | jq -r '.access_token // empty')
  if [ -z "$jeton" ]; then
    echo "ÉCHEC : aucun jeton d'administration. Keycloak répond-il sur $KC ?" >&2
    return 1
  fi
  printf '%s' "$jeton"
}

api_admin() {
  # $1 = méthode, $2 = chemin sous /admin/realms/<realm>, $3 = corps éventuel
  local methode=$1 chemin=$2 corps=${3:-}
  if [ -n "$corps" ]; then
    curl -sS --max-time 20 -w '\n%{http_code}' -X "$methode" \
      "$KC/admin/realms/$REALM/$chemin" \
      -H "Authorization: Bearer $JETON" -H 'Content-Type: application/json' \
      -d "$corps"
  else
    curl -sS --max-time 20 -w '\n%{http_code}' -X "$methode" \
      "$KC/admin/realms/$REALM/$chemin" \
      -H "Authorization: Bearer $JETON"
  fi
}

id_du_client() {
  curl -sS --max-time 20 "$KC/admin/realms/$REALM/clients?clientId=$1" \
    -H "Authorization: Bearer $JETON" | jq -r '.[0].id // empty'
}

id_du_scope() {
  curl -sS --max-time 20 "$KC/admin/realms/$REALM/client-scopes" \
    -H "Authorization: Bearer $JETON" \
    | jq -r --arg n "$1" 'first(.[] | select(.name == $n) | .id) // empty'
}

retirer_client() {
  local identifiant
  identifiant=$(id_du_client "$1")
  [ -n "$identifiant" ] && api_admin DELETE "clients/$identifiant" > /dev/null
  return 0
}

retirer_scope() {
  local identifiant
  identifiant=$(id_du_scope "$1")
  [ -n "$identifiant" ] && api_admin DELETE "client-scopes/$identifiant" > /dev/null
  return 0
}

JETON=$(jeton_admin)

# ─── Mode nettoyage, appelé par cleanup.yaml ──────────────────────────────────
if [ "${1:-}" = "--nettoyer" ]; then
  for nom in "${CLIENTS_DU_TRAVAIL[@]}" "${CLIENTS_OUTILLAGE[@]}"; do
    retirer_client "$nom"
  done
  for nom in "${SCOPES_DU_TRAVAIL[@]}" "${SCOPES_OUTILLAGE[@]}"; do
    retirer_scope "$nom"
  done
  ID_ALICE=$(curl -sS --max-time 20 \
    "$KC/admin/realms/$REALM/users?username=alice&exact=true" \
    -H "Authorization: Bearer $JETON" | jq -r '.[0].id // empty')
  [ -n "$ID_ALICE" ] && api_admin DELETE "users/$ID_ALICE" > /dev/null
  rm -f "$IDENTIFIANTS"
  echo "nettoyage du lab iam-05 terminé"
  exit 0
fi

# ─── Retirer tout travail d'un passage précédent ──────────────────────────────
# Les scopes AVANT les clients : un scope encore attaché à un client ne se
# retire pas proprement, et l'erreur serait avalée par le `|| true` suivant.
/opt/iam-lab/outils/arreter-temoin.sh "$PORT_API"
for nom in "${SCOPES_DU_TRAVAIL[@]}"; do retirer_scope "$nom"; done
for nom in "${CLIENTS_DU_TRAVAIL[@]}"; do retirer_client "$nom"; done

# ─── L'outillage de test, reposé à neuf ───────────────────────────────────────
for nom in "${SCOPES_OUTILLAGE[@]}"; do retirer_scope "$nom"; done
for nom in "${CLIENTS_OUTILLAGE[@]}"; do retirer_client "$nom"; done

# La seconde API : un client sans aucun flux, dont l'identifiant sert
# d'audience. Elle n'expose rien, elle n'existe que pour être une audience.
api_admin POST clients "$(jq -nc '{
  clientId:"autre-api", name:"Une autre API", enabled:true,
  publicClient:false, standardFlowEnabled:false,
  directAccessGrantsEnabled:false, serviceAccountsEnabled:false}')" > /dev/null

# Son scope, qui porte son audience. C'est le mappeur `oidc-audience-mapper`
# qui écrit `aud` dans le jeton : sans lui, un scope ne change pas l'audience.
api_admin POST client-scopes "$(jq -nc '{
  name:"autre:lecture", protocol:"openid-connect",
  attributes:{"include.in.token.scope":"true"}}')" > /dev/null
# L'identifiant se relit, il ne se devine pas : la création rend un en-tête
# `Location`, pas un corps, et le lire demanderait une autre forme d'appel.
ID_SCOPE_AUTRE=$(id_du_scope "autre:lecture")
if [ -z "$ID_SCOPE_AUTRE" ]; then
  echo "ÉCHEC : le scope autre:lecture n'existe pas après sa création." >&2
  exit 1
fi
api_admin POST "client-scopes/$ID_SCOPE_AUTRE/protocol-mappers/models" \
  "$(jq -nc '{
    name:"audience-autre-api", protocol:"openid-connect",
    protocolMapper:"oidc-audience-mapper",
    config:{"included.client.audience":"autre-api",
            "access.token.claim":"true", "id.token.claim":"false"}}')" > /dev/null

# Le client par lequel les tests obtiennent des jetons. Octroi direct activé :
# c'est de l'outillage, pas un exemple à suivre, et le lab 04 a justement
# appris à le fermer.
api_admin POST clients "$(jq -nc '{
  clientId:"notes-cli", name:"Client de test", enabled:true,
  publicClient:true, standardFlowEnabled:false,
  directAccessGrantsEnabled:true, serviceAccountsEnabled:false,
  attributes:{"pkce.code.challenge.method":""}}')" > /dev/null

ID_NOTES_CLI=$(id_du_client "notes-cli")
if [ -z "$ID_NOTES_CLI" ]; then
  echo "ÉCHEC : le client notes-cli n'existe pas après sa création. Sans lui," >&2
  echo "aucun test ne peut obtenir de jeton, et le lab ne serait pas notable." >&2
  exit 1
fi
# Le scope de l'autre API est attaché EN OPTIONNEL : il n'arrive dans un jeton
# que si on le demande. Un scope par défaut serait dans tous les jetons, et le
# test de la mauvaise audience ne mesurerait plus rien.
api_admin PUT "clients/$ID_NOTES_CLI/optional-client-scopes/$ID_SCOPE_AUTRE" > /dev/null

# ─── Le compte humain du lab ──────────────────────────────────────────────────
# `openssl rand`, et surtout pas `tr -dc < /dev/urandom | head -c 24` : sous
# `set -o pipefail`, ce pipeline rend un code non nul parce que `head` ferme le
# tube et que `tr` reçoit SIGPIPE. L'affectation réussit, puis `set -e` tue le
# script.
SECRET_DU_COMPTE=$(openssl rand -hex 12)

# Idempotent, et le secret est TOUJOURS reposé : un POST suivi d'un `|| true`
# avale le 409 d'un compte déjà créé, et le secret reste celui du premier
# passage. Le flux échoue alors sur « Invalid username or password », ce qui
# ressemble à un client mal déclaré.
api_admin POST users "$(jq -nc '{
  username:"alice", enabled:true, emailVerified:true,
  firstName:"Alice", lastName:"Martin", email:"alice@formation.lab"}')" > /dev/null

ID_ALICE=$(curl -sS --max-time 20 \
  "$KC/admin/realms/$REALM/users?username=alice&exact=true" \
  -H "Authorization: Bearer $JETON" | jq -r '.[0].id // empty')
if [ -z "$ID_ALICE" ]; then
  echo "ÉCHEC : alice n'existe pas après sa création." >&2
  exit 1
fi
api_admin PUT "users/$ID_ALICE/reset-password" "$(jq -nc \
  --arg m "$SECRET_DU_COMPTE" '{type:"password", value:$m, temporary:false}')" > /dev/null

# ─── Démarrer l'API dans sa version de départ ─────────────────────────────────
# Démarrée par le setup, pour que l'apprenant voie tout de suite qu'elle
# fonctionne et accepte n'importe quel jeton signé. C'est le constat d'où part
# le challenge.
# LA TRACE EST CRÉÉE AVEC LES BONS DROITS AVANT TOUT DÉMARRAGE.
#
# Mesuré le 2026-10-16, et c'est un silence complet : ce script tourne en root,
# donc la redirection `> api.log` crée un fichier root:root en 0644. L'apprenant
# et la solution de référence relancent ensuite l'API sous `student`, qui ne
# peut pas écrire dedans. Le shell échoue sur la redirection, mais le `&` a déjà
# détaché le sous-shell : le « Permission denied » ne remonte nulle part, la
# tâche réussit, et rien ne tourne.
#
# On ne diagnostique pas cela en lisant le script : on le diagnostique en
# constatant un port vide et un journal qui porte encore la sortie du passage
# précédent.
touch "$API/api.log"
chown student:docker "$API/api.log"
chmod 0660 "$API/api.log"

# `setsid` détache l'API de la session ssh d'Ansible : sans cela, elle est
# tuée à la fermeture de la connexion, et l'apprenant trouve un port muet.
ISSUER="$KC/realms/$REALM" PORT_API="$PORT_API" \
  setsid nohup /opt/iam-lab/appli-temoin/.venv/bin/python "$API/api.py" \
  > "$API/api.log" 2>&1 &

for _ in $(seq 1 30); do
  if curl -sS -o /dev/null --max-time 2 "http://127.0.0.1:$PORT_API/notes"; then
    break
  fi
  sleep 1
done
if ! curl -sS -o /dev/null --max-time 5 "http://127.0.0.1:$PORT_API/notes"; then
  echo "ÉCHEC : l'API de départ ne répond pas sur le port $PORT_API." >&2
  tail -20 "$API/api.log" >&2 || true
  exit 1
fi

# ─── Les identifiants, là où l'apprenant ET les tests les lisent ──────────────
{
  echo "# Posé par le setup du lab iam-05. Jetable, régénéré à chaque run."
  echo "REALM=${REALM}"
  echo "UTILISATEUR=alice"
  printf 'MOT_DE_PASSE=%s\n' "$SECRET_DU_COMPTE"
  echo "CLIENT_DE_TEST=notes-cli"
  echo "AUTRE_API=autre-api"
  echo "SCOPE_AUTRE_API=autre:lecture"
} > "$IDENTIFIANTS"
chown student:docker "$IDENTIFIANTS"
chmod 0640 "$IDENTIFIANTS"

set +x
echo "Situation posée : API de départ en service sur le port $PORT_API."
echo "Elle ne vérifie que la signature. Outillage de test : notes-cli, autre-api."
echo "Identifiants dans $IDENTIFIANTS"
