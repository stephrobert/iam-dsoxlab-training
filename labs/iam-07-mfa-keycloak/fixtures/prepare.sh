#!/usr/bin/env bash
# Pose la situation du lab iam-07, et la retire avec `--nettoyer`.
#
# CE QUE CE SCRIPT NE FAIT PAS : le flux d'authentification, la politique de mot
# de passe, ni le rôle qui cible l'équipe. C'est le travail demandé.
#
# CE QU'IL POSE : deux groupes et deux comptes, un dans chaque, et le client de
# l'application témoin. Les deux comptes ont le même mot de passe et aucun
# second facteur : c'est leur APPARTENANCE qui doit faire la différence, et rien
# d'autre.
#
# POURQUOI DEUX COMPTES ET PAS UN
#
# Un lab qui exigerait un second facteur et le vérifierait sur un seul compte
# serait satisfait par une exigence posée sur TOUT LE MONDE, administrateur
# compris et sans recours. C'est exactement le geste que la fiche appelle un cas
# d'échec. Il faut donc deux comptes dont un seul est concerné.
#
# La trace va dans /var/log/dsoxlab-prepare.log, avec `set -x`, interrompue
# autour de chaque secret : ce journal est collecté par `dsoxlab support`.
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

remettre_le_realm_en_etat() {
  # Le flux de navigateur revient à celui de Keycloak, la politique de mot de
  # passe disparaît, et les flux copiés partent. Sans cela, un lab rejoué
  # hériterait du travail du passage précédent et serait vert sans rien faire.
  local lu nom
  lu=$(admin GET "realms/$REALM")
  # `passwordPolicy` à la CHAÎNE VIDE, et non à `null`.
  #
  # Mesuré le 2026-10-16 : un PUT avec `passwordPolicy: null` est ignoré par
  # Keycloak, qui garde la politique en place. Le nettoyage rendait alors la
  # main sur un realm toujours durci, et les labs suivants auraient échoué sur
  # une exigence de mot de passe qu'ils n'ont pas posée.
  printf '%s' "$lu" \
    | jq '.browserFlow = "browser" | .passwordPolicy = ""' > /tmp/realm-iam-07.json
  admin PUT "realms/$REALM" "$(cat /tmp/realm-iam-07.json)" > /dev/null
  rm -f /tmp/realm-iam-07.json
  # PAR IDENTIFIANT, et non par alias.
  #
  # Mesuré le 2026-10-16 : `DELETE /authentication/flows/{id}` attend un
  # IDENTIFIANT, là où `GET /authentication/flows/{alias}/executions` attend un
  # ALIAS. L'incohérence est dans l'API de Keycloak. Un DELETE par alias rend
  # 404 sans rien supprimer, les flux s'accumulent, et la copie suivante échoue
  # en 409 Conflict sur un nom déjà pris.
  for identifiant in $(admin GET "realms/$REALM/authentication/flows" \
                       | jq -r '.[] | select(.builtIn == false) | .id'); do
    admin DELETE "realms/$REALM/authentication/flows/$identifiant" > /dev/null
  done
  return 0
}

retirer_les_objets_du_lab() {
  local id nom
  for nom in resp-exploitation resp-lecture; do
    id=$(admin GET "realms/$REALM/users?username=$nom&exact=true" \
      | jq -r '.[0].id // empty')
    [ -n "$id" ] && admin DELETE "realms/$REALM/users/$id" > /dev/null
  done
  for id in $(admin GET "realms/$REALM/groups" | jq -r '.[].id'); do
    admin DELETE "realms/$REALM/groups/$id" > /dev/null
  done
  for nom in $(admin GET "realms/$REALM/roles" \
               | jq -r '.[] | select(.name | startswith("default-roles") | not) | .name'); do
    admin DELETE "realms/$REALM/roles/$(printf '%s' "$nom" | jq -sRr @uri)" > /dev/null
  done
  id=$(admin GET "realms/$REALM/clients?clientId=appli-notes" \
    | jq -r '.[0].id // empty')
  [ -n "$id" ] && admin DELETE "realms/$REALM/clients/$id" > /dev/null
  return 0
}

# ─── Mode nettoyage, appelé par cleanup.yaml ──────────────────────────────────
if [ "${1:-}" = "--nettoyer" ]; then
  /opt/iam-lab/outils/arreter-temoin.sh "$PORT_TEMOIN" || true
  rm -f "$APPLI/configuration.json" "$APPLI/temoin.log"
  remettre_le_realm_en_etat
  retirer_les_objets_du_lab
  rm -f "$IDENTIFIANTS"
  echo "nettoyage du lab iam-07 terminé"
  exit 0
fi

# ─── Retirer tout travail d'un passage précédent ──────────────────────────────
/opt/iam-lab/outils/arreter-temoin.sh "$PORT_TEMOIN" || true
rm -f "$APPLI/configuration.json" "$APPLI/temoin.log"
remettre_le_realm_en_etat
retirer_les_objets_du_lab

# ─── Deux groupes, deux comptes, le même mot de passe ─────────────────────────
set +x
SECRET_DES_COMPTES=$(openssl rand -hex 12)
set -x

for groupe in devops lecteurs; do
  admin POST "realms/$REALM/groups" "$(jq -nc --arg n "$groupe" '{name:$n}')" > /dev/null
done

for duo in "resp-exploitation:devops:Camille:Exploitation" \
           "resp-lecture:lecteurs:Yann:Lecture"; do
  compte=${duo%%:*}
  reste=${duo#*:}
  groupe=${reste%%:*}
  reste=${reste#*:}
  prenom=${reste%%:*}
  nom=${reste#*:}
  admin POST "realms/$REALM/users" "$(jq -nc \
    --arg u "$compte" --arg p "$prenom" --arg n "$nom" \
    --arg e "$compte@formation.lab" '{
    username:$u, enabled:true, emailVerified:true,
    firstName:$p, lastName:$n, email:$e}')" > /dev/null
  identifiant=$(admin GET "realms/$REALM/users?username=$compte&exact=true" \
    | jq -r '.[0].id // empty')
  if [ -z "$identifiant" ]; then
    echo "ÉCHEC : $compte n'existe pas après sa création." >&2
    exit 1
  fi
  set +x
  admin PUT "realms/$REALM/users/$identifiant/reset-password" \
    "$(jq -nc --arg m "$SECRET_DES_COMPTES" \
       '{type:"password", value:$m, temporary:false}')" > /dev/null
  set -x
  id_groupe=$(admin GET "realms/$REALM/groups" \
    | jq -r --arg n "$groupe" '.[] | select(.name == $n) | .id')
  admin PUT "realms/$REALM/users/$identifiant/groups/$id_groupe" '{}' > /dev/null
done

# ─── Le client de l'application témoin ────────────────────────────────────────
admin POST "realms/$REALM/clients" "$(jq -nc '{
  clientId:"appli-notes", name:"Application notes", enabled:true,
  publicClient:true, standardFlowEnabled:true, implicitFlowEnabled:false,
  directAccessGrantsEnabled:false, serviceAccountsEnabled:false,
  redirectUris:["http://127.0.0.1:9080/callback"],
  webOrigins:["http://127.0.0.1:9080"],
  attributes:{"pkce.code.challenge.method":"S256"}}')" > /dev/null

cat > "$APPLI/configuration.json" <<CONF
{
  "issuer": "$KC/realms/$REALM",
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
set +x
{
  echo "# Posé par le setup du lab iam-07. Jetable."
  echo "REALM=${REALM}"
  echo "GROUPE_CONCERNE=devops"
  echo "GROUPE_EPARGNE=lecteurs"
  echo "COMPTE_CONCERNE=resp-exploitation"
  echo "COMPTE_EPARGNE=resp-lecture"
  printf 'MOT_DE_PASSE=%s\n' "$SECRET_DES_COMPTES"
  echo "APPLICATION=http://127.0.0.1:${PORT_TEMOIN}"
} > "$IDENTIFIANTS"
chown student:docker "$IDENTIFIANTS"
chmod 0640 "$IDENTIFIANTS"
set -x

# ─── Contrôler l'état posé ────────────────────────────────────────────────────
# Les DEUX comptes doivent se connecter sans second facteur au départ. Sans ce
# contrôle, un lab parti d'un realm où le flux était déjà modifié serait vert
# avant tout travail.
set +x
for compte in resp-exploitation resp-lecture; do
  curl -sS --max-time 10 "http://127.0.0.1:$PORT_TEMOIN/deconnexion" > /dev/null
  trouve=$(sudo -u student python3 /opt/iam-lab/outils/parcours.py \
    --depart "http://127.0.0.1:$PORT_TEMOIN/connexion" \
    --utilisateur "$compte" --mot-de-passe "$SECRET_DES_COMPTES" \
    --attendre-texte "Connecté en tant que $compte" --tours 25 2>/dev/null \
    | jq -r '.texte_trouve // false')
  if [ "$trouve" != "true" ]; then
    set -x
    echo "ÉCHEC : $compte ne se connecte pas dans la situation de départ." >&2
    echo "Le flux de navigateur du realm est-il bien celui de Keycloak ?" >&2
    exit 1
  fi
done
set -x

set +x
echo "Situation posée : deux groupes, deux comptes, aucun second facteur, et le"
echo "flux de navigateur de Keycloak intact. Les deux comptes se connectent."
echo "Identifiants dans $IDENTIFIANTS"
