#!/usr/bin/env bash
# Pose la situation du lab iam-12 : une intégration CASSÉE, et la retire avec
# `--nettoyer`.
#
# CINQ PANNES, UNE SEULE TIRÉE AU HASARD
#
# Toutes mesurées le 2026-10-16, et chacune donne un symptôme différent :
#
#   1  URI de redirection fautive côté Keycloak
#      « Invalid parameter: redirect_uri », événement invalid_redirect_uri
#   2  issuer fautif côté application
#      « Client not found » sur le MAUVAIS realm, et AUCUN événement dans le bon
#   3  client passé en confidentiel
#      « unauthorized_client », événement invalid_client_credentials
#   4  client désactivé
#      « Client disabled. », événement client_disabled
#   5  flux de code fermé
#      « Standard flow is disabled for the client », événement not_allowed
#
# CE QUI N'EST PAS ÉCRIT SUR LA MACHINE : laquelle a été tirée. Le journal note
# le NUMÉRO de la variante, pas son contenu, et la liste des variantes n'existe
# que dans ce fichier, qui vit dans le dépôt. Un apprenant qui lirait le journal
# avec sudo n'y apprendrait donc rien d'utile.
#
# Les ÉVÉNEMENTS du realm sont activés, sans quoi le journal que le lab demande
# de lire serait vide, et l'apprenant chercherait longtemps.
set -euo pipefail

JOURNAL=/var/log/dsoxlab-prepare.log
exec > >(tee -a "$JOURNAL") 2>&1
set -x

KC=http://127.0.0.1:8080
REALM=formation
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
set -x
if [ -z "$JETON" ]; then
  echo "ÉCHEC : aucun jeton d'administration. Keycloak répond-il sur $KC ?" >&2
  exit 1
fi

admin() {
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

retirer_le_client() {
  local id
  id=$(admin GET "realms/$REALM/clients?clientId=appli-notes" \
    | jq -r '.[0].id // empty')
  [ -n "$id" ] && admin DELETE "realms/$REALM/clients/$id" > /dev/null
  return 0
}

# ─── Mode nettoyage, appelé par cleanup.yaml ──────────────────────────────────
if [ "${1:-}" = "--nettoyer" ]; then
  /opt/iam-lab/outils/arreter-temoin.sh "$PORT_TEMOIN" || true
  rm -f "$APPLI/configuration.json" "$APPLI/temoin.log"
  retirer_le_client
  ID_ALICE=$(admin GET "realms/$REALM/users?username=alice&exact=true" \
    | jq -r '.[0].id // empty')
  [ -n "$ID_ALICE" ] && admin DELETE "realms/$REALM/users/$ID_ALICE" > /dev/null
  # Les événements sont remis dans leur état d'origine : les laisser activés
  # ferait grossir la base sans fin sur une machine de formation.
  admin PUT "realms/$REALM/events/config" "$(jq -nc '{
    eventsEnabled:false, eventsListeners:["jboss-logging"],
    enabledEventTypes:[], adminEventsEnabled:false,
    adminEventsDetailsEnabled:false}')" > /dev/null
  rm -f "$IDENTIFIANTS"
  echo "nettoyage du lab iam-12 terminé"
  exit 0
fi

# ─── Partir d'une intégration SAINE ───────────────────────────────────────────
/opt/iam-lab/outils/arreter-temoin.sh "$PORT_TEMOIN" || true
rm -f "$APPLI/configuration.json" "$APPLI/temoin.log"
retirer_le_client

set +x
SECRET_DU_COMPTE=$(openssl rand -hex 12)
set -x

ID_ALICE=$(admin GET "realms/$REALM/users?username=alice&exact=true" \
  | jq -r '.[0].id // empty')
if [ -z "$ID_ALICE" ]; then
  admin POST "realms/$REALM/users" "$(jq -nc '{
    username:"alice", enabled:true, emailVerified:true,
    firstName:"Aline", lastName:"Dupont", email:"aline@formation.lab"}')" > /dev/null
  ID_ALICE=$(admin GET "realms/$REALM/users?username=alice&exact=true" \
    | jq -r '.[0].id // empty')
fi
if [ -z "$ID_ALICE" ]; then
  echo "ÉCHEC : alice n'existe pas après sa création." >&2
  exit 1
fi
set +x
admin PUT "realms/$REALM/users/$ID_ALICE/reset-password" \
  "$(jq -nc --arg m "$SECRET_DU_COMPTE" \
     '{type:"password", value:$m, temporary:false}')" > /dev/null
set -x

# Les événements, que le lab demande de lire. Sans eux, le journal est vide.
admin PUT "realms/$REALM/events/config" "$(jq -nc '{
  eventsEnabled:true, eventsListeners:["jboss-logging"],
  enabledEventTypes:[], adminEventsEnabled:true,
  adminEventsDetailsEnabled:false}')" > /dev/null

# ─── Tirer la panne, et l'appliquer ───────────────────────────────────────────
# `shuf -n1` plutôt que `$RANDOM % 5` : le modulo d'une variable du shell est
# mal distribué sur de petites plages, et un lab qui tirerait toujours la même
# panne cesserait d'en être un.
VARIANTE=$(shuf -i 1-5 -n 1)

# Le client, dans sa forme SAINE. Chaque variante en modifie UN point.
CLIENT_SAIN=$(jq -nc --arg r "http://127.0.0.1:$PORT_TEMOIN/callback" \
  --arg o "http://127.0.0.1:$PORT_TEMOIN" '{
  clientId:"appli-notes", name:"Application notes", enabled:true,
  publicClient:true, standardFlowEnabled:true, implicitFlowEnabled:false,
  directAccessGrantsEnabled:false, serviceAccountsEnabled:false,
  redirectUris:[$r], webOrigins:[$o],
  attributes:{"pkce.code.challenge.method":"S256"}}')

# La configuration de l'application, dans sa forme SAINE.
ISSUER_SAIN="$KC/realms/$REALM"

CLIENT_POSE=$CLIENT_SAIN
ISSUER_POSE=$ISSUER_SAIN

case "$VARIANTE" in
  1) CLIENT_POSE=$(printf '%s' "$CLIENT_SAIN" | jq \
       --arg r "http://127.0.0.1:$PORT_TEMOIN/retour" '.redirectUris = [$r]') ;;
  2) ISSUER_POSE="$KC/realms/master" ;;
  3) CLIENT_POSE=$(printf '%s' "$CLIENT_SAIN" | jq '.publicClient = false') ;;
  4) CLIENT_POSE=$(printf '%s' "$CLIENT_SAIN" | jq '.enabled = false') ;;
  5) CLIENT_POSE=$(printf '%s' "$CLIENT_SAIN" | jq '.standardFlowEnabled = false') ;;
  *) echo "ÉCHEC : variante $VARIANTE inattendue." >&2; exit 1 ;;
esac

admin POST "realms/$REALM/clients" "$CLIENT_POSE" > /dev/null

cat > "$APPLI/configuration.json" <<CONF
{
  "issuer": "$ISSUER_POSE",
  "client_id": "appli-notes",
  "redirect_uri": "http://127.0.0.1:$PORT_TEMOIN/callback"
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
# Le compte de test, et RIEN sur la panne. Le numéro de variante n'est écrit
# nulle part sur la machine : la liste des variantes vit dans ce script, qui
# est dans le dépôt, et le journal ne garde que les commandes.
set +x
{
  echo "# Posé par le setup du lab iam-12. Jetable."
  echo "REALM=${REALM}"
  echo "CLIENT=appli-notes"
  echo "UTILISATEUR=alice"
  printf 'MOT_DE_PASSE=%s\n' "$SECRET_DU_COMPTE"
  echo "APPLICATION=http://127.0.0.1:${PORT_TEMOIN}"
  echo "CONFIGURATION_APPLI=${APPLI}/configuration.json"
} > "$IDENTIFIANTS"
chown student:docker "$IDENTIFIANTS"
chmod 0640 "$IDENTIFIANTS"
set -x

# ─── Contrôler que l'intégration est bien CASSÉE ──────────────────────────────
# Un lab de dépannage dont l'intégration fonctionne n'a pas d'objet, et le
# contrôle négatif serait vert. On vérifie donc que le parcours échoue, ce qui
# est l'inverse de tous les autres labs du catalogue.
set +x
RESULTAT=$(sudo -u student python3 /opt/iam-lab/outils/parcours.py \
  --depart "http://127.0.0.1:$PORT_TEMOIN/connexion" \
  --utilisateur alice --mot-de-passe "$SECRET_DU_COMPTE" \
  --attendre-texte "Connecté en tant que alice" --tours 25 2>/dev/null \
  | jq -r '.texte_trouve // false')
set -x
if [ "$RESULTAT" = "true" ]; then
  echo "ÉCHEC : l'intégration fonctionne alors qu'une panne a été injectée." >&2
  echo "La variante $VARIANTE n'a pas eu l'effet attendu : le lab serait vert" >&2
  echo "avant tout travail." >&2
  exit 1
fi

set +x
echo "Situation posée : l'intégration de l'application témoin est CASSÉE."
echo "Une panne sur cinq a été tirée au hasard. L'application répond sur le"
echo "port $PORT_TEMOIN, et sa connexion échoue."
echo "Identifiants dans $IDENTIFIANTS"
