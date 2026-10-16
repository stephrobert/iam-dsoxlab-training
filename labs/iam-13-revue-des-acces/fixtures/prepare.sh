#!/usr/bin/env bash
# Pose la situation du lab iam-13, et la retire avec `--nettoyer`.
#
# CE QU'IL POSE : trois comptes locaux, deux groupes, et UN ACCÈS INJUSTIFIÉ
# qu'une revue doit trouver. Un compte porte aussi un attribut qui le marque
# comme inactif depuis longtemps, pour que le workflow ait quelque chose à
# mordre.
#
# CE QUE CE SCRIPT NE FAIT PAS : ouvrir l'API SCIM, créer son client, écrire le
# workflow, ni la revue. C'est le travail demandé. Il REFERME d'ailleurs l'API
# SCIM si un passage précédent l'avait ouverte.
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
REVUE=/opt/iam-lab/revue-des-acces.json

#: Les comptes locaux du lab.
COMPTES=(aline bruno dormeur)
#: Le rôle qui ne devrait appartenir à personne, et que la revue doit trouver.
ROLE_INJUSTIFIE=acces-production-temporaire
#: Qui le porte, à tort.
PORTEUR=bruno

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

refermer_le_realm() {
  # L'API SCIM est REFERMÉE, et les workflows retirés : c'est le travail du lab,
  # et un lab parti d'un realm déjà ouvert serait vert avant tout travail.
  #
  # `scimApiEnabled` se pose à la RACINE de la représentation du realm, pas dans
  # ses attributs. Mesuré le 2026-10-16 : dans `attributes`, le PUT rend 204 et
  # la valeur relue reste `false`.
  local lu identifiant
  lu=$(admin GET "realms/$REALM")
  printf '%s' "$lu" | jq '.scimApiEnabled = false' > /tmp/realm-iam-13.json
  admin PUT "realms/$REALM" "$(cat /tmp/realm-iam-13.json)" > /dev/null
  rm -f /tmp/realm-iam-13.json

  # L'API des workflows rend du YAML, pas du JSON : les identifiants se lisent
  # au motif. Mesuré le 2026-10-16.
  for identifiant in $(admin GET "realms/$REALM/workflows" \
                       | grep -oE 'id: "[0-9a-f-]{36}"' \
                       | grep -oE '[0-9a-f-]{36}'); do
    admin DELETE "realms/$REALM/workflows/$identifiant" > /dev/null 2>&1 || true
  done
  return 0
}

retirer_les_objets() {
  local id nom
  for nom in "${COMPTES[@]}" scim-nouvelle; do
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
  for nom in scim-client appli-notes; do
    id=$(admin GET "realms/$REALM/clients?clientId=$nom" | jq -r '.[0].id // empty')
    [ -n "$id" ] && admin DELETE "realms/$REALM/clients/$id" > /dev/null
  done
  return 0
}

# ─── Mode nettoyage, appelé par cleanup.yaml ──────────────────────────────────
if [ "${1:-}" = "--nettoyer" ]; then
  refermer_le_realm
  retirer_les_objets
  rm -f "$IDENTIFIANTS" "$REVUE"
  echo "nettoyage du lab iam-13 terminé"
  exit 0
fi

# ─── Retirer tout travail d'un passage précédent ──────────────────────────────
refermer_le_realm
retirer_les_objets
rm -f "$REVUE"

# ─── Trois comptes, deux groupes ──────────────────────────────────────────────
set +x
SECRET_DES_COMPTES=$(openssl rand -hex 12)
set -x

for groupe in exploitation lecture; do
  admin POST "realms/$REALM/groups" "$(jq -nc --arg n "$groupe" '{name:$n}')" > /dev/null
done

# `dormeur` porte un attribut qui dit sa dernière connexion, très ancienne.
# C'est ce qu'un workflow de cycle de vie lira pour décider.
for duo in "aline:exploitation:Aline:Dupont" \
           "bruno:lecture:Bruno:Keller" \
           "dormeur:lecture:Didier:Dormeur"; do
  compte=${duo%%:*}
  reste=${duo#*:}
  groupe=${reste%%:*}
  reste=${reste#*:}
  prenom=${reste%%:*}
  nom=${reste#*:}
  if [ "$compte" = "dormeur" ]; then
    corps=$(jq -nc --arg u "$compte" --arg p "$prenom" --arg n "$nom" \
      --arg e "$compte@formation.lab" '{
      username:$u, enabled:true, emailVerified:true,
      firstName:$p, lastName:$n, email:$e,
      attributes:{"derniere_connexion":["2024-02-14"]}}')
  else
    corps=$(jq -nc --arg u "$compte" --arg p "$prenom" --arg n "$nom" \
      --arg e "$compte@formation.lab" '{
      username:$u, enabled:true, emailVerified:true,
      firstName:$p, lastName:$n, email:$e}')
  fi
  admin POST "realms/$REALM/users" "$corps" > /dev/null
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

# ─── L'ACCÈS INJUSTIFIÉ, que la revue doit trouver ────────────────────────────
# Un rôle au nom explicite, accordé DIRECTEMENT à quelqu'un de l'équipe de
# lecture. Personne ne sait plus pourquoi, et aucune revue par groupes ne le
# montrerait.
admin POST "realms/$REALM/roles" "$(jq -nc --arg n "$ROLE_INJUSTIFIE" '{
  name:$n,
  description:"Accordé en urgence le 12 mars, jamais retiré. Aucun ticket."}')" \
  > /dev/null
LE_ROLE=$(admin GET "realms/$REALM/roles/$ROLE_INJUSTIFIE")
ID_PORTEUR=$(admin GET "realms/$REALM/users?username=$PORTEUR&exact=true" \
  | jq -r '.[0].id // empty')
admin POST "realms/$REALM/users/$ID_PORTEUR/role-mappings/realm" \
  "$(printf '[%s]' "$LE_ROLE")" > /dev/null

# ─── Ce que l'apprenant doit savoir pour commencer ────────────────────────────
set +x
{
  echo "# Posé par le setup du lab iam-13. Jetable."
  echo "REALM=${REALM}"
  echo "COMPTES=${COMPTES[*]}"
  printf 'MOT_DE_PASSE=%s\n' "$SECRET_DES_COMPTES"
  echo "COMPTE_INACTIF=dormeur"
  echo "ROLE_INJUSTIFIE=${ROLE_INJUSTIFIE}"
  echo "PORTEUR_DU_ROLE=${PORTEUR}"
  echo "COMPTE_A_PROVISIONNER=scim-nouvelle"
  echo "CLIENT_SCIM_ATTENDU=scim-client"
  echo "URL_SCIM=${KC}/realms/${REALM}/scim/v2"
  echo "FICHIER_DE_REVUE=${REVUE}"
} > "$IDENTIFIANTS"
chown student:docker "$IDENTIFIANTS"
chmod 0640 "$IDENTIFIANTS"
set -x

# ─── Contrôler l'état posé ────────────────────────────────────────────────────
# L'API SCIM doit être FERMÉE, et aucun workflow ne doit exister. Sans ce
# contrôle, un lab parti d'un realm déjà ouvert serait vert avant tout travail.
SCIM_OUVERT=$(admin GET "realms/$REALM" | jq -r '.scimApiEnabled // false')
CODE_SCIM=$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' \
  "$KC/realms/$REALM/scim/v2/ServiceProviderConfig")
WORKFLOWS=$(admin GET "realms/$REALM/workflows" | grep -c 'name:' || true)
if [ "$SCIM_OUVERT" = "true" ] || [ "$CODE_SCIM" != "404" ] || [ "$WORKFLOWS" -ne 0 ]; then
  echo "ÉCHEC : la situation de départ n'est pas celle attendue." >&2
  echo "scimApiEnabled=$SCIM_OUVERT code_scim=$CODE_SCIM workflows=$WORKFLOWS" >&2
  exit 1
fi

set +x
echo "Situation posée : trois comptes, deux groupes, un rôle injustifié porté"
echo "par $PORTEUR, l'API SCIM fermée et aucun workflow."
echo "Identifiants dans $IDENTIFIANTS"
