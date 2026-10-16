#!/usr/bin/env bash
# Pose la situation du lab iam-11, et la retire avec `--nettoyer`.
#
# LE FOURNISSEUR EXTERNE EST UN SECOND REALM, pour les mêmes raisons qu'au lab
# 06 : c'est l'image du socle, déjà épinglée et maintenue, rien à télécharger,
# et le lab montre les deux côtés. Ici le realm « formation » est le COURTIER,
# et le second realm joue l'entreprise partenaire. C'est l'inverse du lab 06,
# où « formation » émettait.
#
# CE QUE CE SCRIPT NE FAIT PAS : déclarer le fournisseur d'identité dans le
# courtier, ni son groupe par défaut. C'est le travail demandé.
#
# CE QU'IL POSE : le realm partenaire avec un compte et un client OIDC prêt,
# parce que dans la vraie vie c'est le partenaire qui vous le fournit, pas vous
# qui le créez. Et un compte local de MÊME ADRESSE dans le courtier, qui est le
# piège du lab.
#
# La trace va dans /var/log/dsoxlab-prepare.log, avec `set -x`, interrompue
# autour de chaque secret : ce journal est collecté par `dsoxlab support`.
set -euo pipefail

JOURNAL=/var/log/dsoxlab-prepare.log
exec > >(tee -a "$JOURNAL") 2>&1
set -x

KC=http://127.0.0.1:8080
COURTIER=formation
EXTERNE=entreprise-externe
ALIAS=oidc-partenaire
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

nettoyer_le_courtier() {
  local alias_lu id
  for alias_lu in $(admin GET "realms/$COURTIER/identity-provider/instances" \
                    | jq -r '.[].alias'); do
    admin DELETE "realms/$COURTIER/identity-provider/instances/$alias_lu" > /dev/null
  done
  for nom in bob dora chloe; do
    id=$(admin GET "realms/$COURTIER/users?username=$nom&exact=true" \
      | jq -r '.[0].id // empty')
    [ -n "$id" ] && admin DELETE "realms/$COURTIER/users/$id" > /dev/null
  done
  # Les groupes par défaut doivent être détachés AVANT que le groupe parte :
  # un groupe par défaut supprimé laisse une référence morte que Keycloak
  # signale à chaque création de compte.
  for id in $(admin GET "realms/$COURTIER/default-groups" | jq -r '.[].id'); do
    admin DELETE "realms/$COURTIER/default-groups/$id" > /dev/null
  done
  for id in $(admin GET "realms/$COURTIER/groups" | jq -r '.[].id'); do
    admin DELETE "realms/$COURTIER/groups/$id" > /dev/null
  done
  id=$(admin GET "realms/$COURTIER/clients?clientId=appli-notes" \
    | jq -r '.[0].id // empty')
  [ -n "$id" ] && admin DELETE "realms/$COURTIER/clients/$id" > /dev/null
  return 0
}

# ─── Mode nettoyage, appelé par cleanup.yaml ──────────────────────────────────
if [ "${1:-}" = "--nettoyer" ]; then
  /opt/iam-lab/outils/arreter-temoin.sh "$PORT_TEMOIN" || true
  rm -f "$APPLI/configuration.json" "$APPLI/temoin.log"
  admin DELETE "realms/$EXTERNE" > /dev/null
  nettoyer_le_courtier
  rm -f "$IDENTIFIANTS"
  echo "nettoyage du lab iam-11 terminé"
  exit 0
fi

# ─── Retirer tout travail d'un passage précédent ──────────────────────────────
/opt/iam-lab/outils/arreter-temoin.sh "$PORT_TEMOIN" || true
rm -f "$APPLI/configuration.json" "$APPLI/temoin.log"
admin DELETE "realms/$EXTERNE" > /dev/null
nettoyer_le_courtier

# ─── Le realm du partenaire, son compte et son client ─────────────────────────
set +x
SECRET_DU_COMPTE=$(openssl rand -hex 12)
SECRET_DU_CLIENT=$(openssl rand -hex 16)
set -x

admin POST realms "$(jq -nc --arg r "$EXTERNE" '{
  realm:$r, enabled:true, displayName:"Entreprise partenaire"}')" > /dev/null

# DEUX comptes chez le partenaire, et c'est le sujet du lab.
#
#   dora  son adresse ne correspond à personne dans le courtier : sa connexion
#         doit ABOUTIR, et son compte arriver dans le groupe par défaut.
#   bob   son adresse est celle d'un compte LOCAL du courtier : le flux de
#         premier login doit S'ARRÊTER et demander, au lieu de lier.
#
# Mesuré le 2026-10-16 : avec le flux que Keycloak fournit, bob tombe sur
# « Account already exists. User with email bob@partenaire.example already
# exists. How do you want to continue? ». C'est le bon comportement, et c'est
# ce que le lab fait prouver.
for duo in "dora:Dora:Entrante" "bob:Bob:Externe"; do
  compte=${duo%%:*}
  reste=${duo#*:}
  prenom=${reste%%:*}
  nom=${reste#*:}
  admin POST "realms/$EXTERNE/users" "$(jq -nc \
    --arg u "$compte" --arg p "$prenom" --arg n "$nom" \
    --arg e "$compte@partenaire.example" '{
    username:$u, enabled:true, emailVerified:true,
    firstName:$p, lastName:$n, email:$e}')" > /dev/null
  identifiant=$(admin GET "realms/$EXTERNE/users?username=$compte&exact=true" \
    | jq -r '.[0].id // empty')
  if [ -z "$identifiant" ]; then
    echo "ÉCHEC : $compte n'existe pas dans le realm partenaire." >&2
    exit 1
  fi
  set +x
  admin PUT "realms/$EXTERNE/users/$identifiant/reset-password" \
    "$(jq -nc --arg m "$SECRET_DU_COMPTE" \
       '{type:"password", value:$m, temporary:false}')" > /dev/null
  set -x
done
set +x

# Le client que le partenaire fournit au courtier. Son adresse de retour
# découle de l'ALIAS que l'apprenant doit employer, et c'est pourquoi l'alias
# est imposé : le partenaire a déjà déclaré cette adresse chez lui.
admin POST "realms/$EXTERNE/clients" "$(jq -nc \
  --arg s "$SECRET_DU_CLIENT" \
  --arg r "$KC/realms/$COURTIER/broker/$ALIAS/endpoint" '{
  clientId:"courtier-formation", name:"Courtier de la formation", enabled:true,
  publicClient:false, secret:$s,
  standardFlowEnabled:true, implicitFlowEnabled:false,
  directAccessGrantsEnabled:false, serviceAccountsEnabled:false,
  redirectUris:[$r]}')" > /dev/null
set -x

# ─── LE PIÈGE : un compte local qui porte l'adresse de « bob » ───────────────
# Il existe pour une seule raison : si l'apprenant choisit un flux de premier
# login qui lie automatiquement sur l'adresse, l'inconnu prendra le contrôle de
# CE compte. C'est une prise de contrôle de compte, et elle se fait en silence.
#
# Avec le flux que Keycloak fournit, la connexion de bob s'arrête au contraire
# sur un écran qui nomme le conflit. C'est ce que le lab fait prouver, et c'est
# une preuve POSITIVE du refus, qui vaut mieux que de lire un réglage.
admin POST "realms/$COURTIER/users" "$(jq -nc '{
  username:"chloe", enabled:true, emailVerified:true,
  firstName:"Chloe", lastName:"Interne", email:"bob@partenaire.example"}')" > /dev/null

# ─── L'application témoin, pointée sur le COURTIER ────────────────────────────
admin POST "realms/$COURTIER/clients" "$(jq -nc '{
  clientId:"appli-notes", name:"Application notes", enabled:true,
  publicClient:true, standardFlowEnabled:true, implicitFlowEnabled:false,
  directAccessGrantsEnabled:false, serviceAccountsEnabled:false,
  redirectUris:["http://127.0.0.1:9080/callback"],
  webOrigins:["http://127.0.0.1:9080"],
  attributes:{"pkce.code.challenge.method":"S256"}}')" > /dev/null

cat > "$APPLI/configuration.json" <<CONF
{
  "issuer": "$KC/realms/$COURTIER",
  "client_id": "appli-notes",
  "redirect_uri": "http://127.0.0.1:$PORT_TEMOIN/callback",
  "idp_hint": "$ALIAS"
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
  echo "# Posé par le setup du lab iam-11. Jetable."
  echo "REALM_COURTIER=${COURTIER}"
  echo "REALM_PARTENAIRE=${EXTERNE}"
  echo "ALIAS_ATTENDU=${ALIAS}"
  echo "DECOUVERTE_PARTENAIRE=${KC}/realms/${EXTERNE}/.well-known/openid-configuration"
  echo "CLIENT_FOURNI=courtier-formation"
  printf 'SECRET_FOURNI=%s\n' "$SECRET_DU_CLIENT"
  echo "UTILISATEUR_QUI_ENTRE=dora"
  echo "UTILISATEUR_EN_CONFLIT=bob"
  printf 'MOT_DE_PASSE_EXTERNE=%s\n' "$SECRET_DU_COMPTE"
  echo "GROUPE_ATTENDU=partenaires"
  echo "COMPTE_LOCAL_PIEGE=chloe"
} > "$IDENTIFIANTS"
chown student:docker "$IDENTIFIANTS"
chmod 0640 "$IDENTIFIANTS"
set -x

# ─── Contrôler l'état posé ────────────────────────────────────────────────────
if [ "$(admin GET "realms/$EXTERNE" | jq -r '.realm // empty')" != "$EXTERNE" ]; then
  echo "ÉCHEC : le realm $EXTERNE n'existe pas après sa création." >&2
  exit 1
fi
if [ "$(admin GET "realms/$COURTIER/identity-provider/instances" | jq 'length')" -ne 0 ]; then
  echo "ÉCHEC : le courtier porte déjà un fournisseur d'identité." >&2
  exit 1
fi

set +x
echo "Situation posée : realm $EXTERNE avec dora et bob et son client, courtier sans"
echo "aucun fournisseur d'identité, et un compte local « chloe » qui porte la"
echo "MÊME adresse que bob."
echo "Identifiants dans $IDENTIFIANTS"
