#!/usr/bin/env bash
# Pose la situation du lab iam-03, et la retire avec `--nettoyer`.
#
# CE QUE CE SCRIPT NE FAIT PAS : déclarer la fédération ni le mappeur de
# groupes. C'est le travail demandé.
#
# CE QU'IL POSE : l'annuaire peuplé, c'est-à-dire le résultat du lab 01. Les
# labs se jouent dans n'importe quel ordre, et celui-ci suppose un annuaire
# rempli : il le remplit donc lui-même, avec les mêmes personnes et les mêmes
# groupes.
#
# Il pose aussi `notes-cli`, un client public à octroi direct, par lequel les
# tests vérifient qu'un compte de l'annuaire obtient un jeton. C'est de
# l'outillage de mesure, pas un exemple à suivre : le lab 04 apprend justement
# à fermer cet octroi.
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
WEB=http://127.0.0.1:17170
LDAP=ldap://127.0.0.1:3890

if [ ! -r "$SOCLE_ENV" ]; then
  echo "ÉCHEC : $SOCLE_ENV est absent ou illisible. Le socle IAM n'est pas" >&2
  echo "installé, ou ce script tourne sous un compte hors du groupe docker." >&2
  exit 1
fi

# `cut -d= -f2-`, ET PAS `-f2` : le DN de base vaut `dc=formation,dc=lab`, et
# `-f2` le couperait au premier `=` en rendant `dc`. Les requêtes échoueraient
# alors sur « Naming violation (64) », qui désigne la requête et non la variable.
BASE=$(grep '^LLDAP_BASE_DN=' "$SOCLE_ENV" | cut -d= -f2-)
ADMIN_DN="uid=admin,ou=people,$BASE"

set +x
MDP_LDAP=$(grep '^LLDAP_ADMIN_PASSWORD=' "$SOCLE_ENV" | cut -d= -f2-)
KC_USER=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME=' "$SOCLE_ENV" | cut -d= -f2-)
KC_MDP=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD=' "$SOCLE_ENV" | cut -d= -f2-)
set -x

#: Les personnes de l'annuaire, identiques à celles du lab 01.
PERSONNES=(aline bruno chloe)
#: Les groupes, et leurs membres.
GROUPE_DEVOPS=(aline bruno)
GROUPE_LECTEURS=(bruno chloe)

jeton_keycloak() {
  set +x
  local jeton
  jeton=$(curl -sS --max-time 20 -X POST \
    "$KC/realms/master/protocol/openid-connect/token" \
    -d grant_type=password -d client_id=admin-cli \
    -d "username=$KC_USER" -d "password=$KC_MDP" \
    | jq -r '.access_token // empty')
  set -x
  if [ -z "$jeton" ]; then
    echo "ÉCHEC : aucun jeton d'administration Keycloak." >&2
    return 1
  fi
  printf '%s' "$jeton"
}

jeton_lldap() {
  set +x
  local jeton
  jeton=$(curl -sS --max-time 20 -X POST "$WEB/auth/simple/login" \
    -H 'Content-Type: application/json' \
    -d "$(jq -nc --arg m "$MDP_LDAP" '{username:"admin", password:$m}')" \
    | jq -r '.token // empty')
  set -x
  if [ -z "$jeton" ]; then
    echo "ÉCHEC : aucun jeton de l'API LLDAP. L'annuaire répond-il ?" >&2
    return 1
  fi
  printf '%s' "$jeton"
}

kc() { # $1 méthode, $2 chemin sous /admin/realms/<realm>, $3 corps
  set +x
  local m=$1 c=$2 b=${3:-}
  if [ -n "$b" ]; then
    curl -sS --max-time 60 -X "$m" "$KC/admin/realms/$REALM/$c" \
      -H "Authorization: Bearer $JETON_KC" -H 'Content-Type: application/json' -d "$b"
  else
    curl -sS --max-time 60 -X "$m" "$KC/admin/realms/$REALM/$c" \
      -H "Authorization: Bearer $JETON_KC"
  fi
  set -x
}

lldap_api() { # $1 corps JSON
  set +x
  curl -sS --max-time 20 -X POST "$WEB/api/graphql" \
    -H "Authorization: Bearer $JETON_LDAP" -H 'Content-Type: application/json' \
    -d "$1"
  set -x
}

retirer_la_federation() {
  # Retirer la fédération retire AUSSI les comptes qu'elle a importés : ils
  # n'existent dans Keycloak que par elle. C'est voulu, et c'est ce qui rend le
  # nettoyage simple.
  local id_realm id
  id_realm=$(kc GET '' | jq -r .id)
  for id in $(kc GET "components?parent=$id_realm&type=org.keycloak.storage.UserStorageProvider" \
              | jq -r '.[].id'); do
    kc DELETE "components/$id" > /dev/null
  done
}

retirer_les_groupes_keycloak() {
  # Les groupes importés survivent au retrait de la fédération : ils sont des
  # groupes Keycloak ordinaires une fois créés. Il faut donc les retirer à part,
  # sinon le test d'appartenance serait vert sur un groupe vide hérité.
  local id
  for id in $(kc GET groups | jq -r '.[].id'); do
    kc DELETE "groups/$id" > /dev/null
  done
}

vider_l_annuaire() {
  local compte groupes id
  set +x
  for compte in "${PERSONNES[@]}"; do
    ldapdelete -x -H "$LDAP" -D "$ADMIN_DN" -w "$MDP_LDAP" \
      "uid=$compte,ou=people,$BASE" 2>/dev/null || true
  done
  set -x
  groupes=$(lldap_api '{"query":"{ groups { id displayName } }"}' \
    | jq -r '.data.groups[] | select(.displayName == "devops" or .displayName == "lecteurs") | .id')
  for id in $groupes; do
    lldap_api "$(jq -nc --argjson g "$id" \
      '{query:"mutation($g: Int!) { deleteGroup(groupId: $g) { ok } }", variables:{g:$g}}')" \
      > /dev/null
  done
}

JETON_KC=$(jeton_keycloak)
JETON_LDAP=$(jeton_lldap)

# ─── Mode nettoyage, appelé par cleanup.yaml ──────────────────────────────────
if [ "${1:-}" = "--nettoyer" ]; then
  retirer_la_federation
  retirer_les_groupes_keycloak
  vider_l_annuaire
  ID_CLI=$(kc GET "clients?clientId=notes-cli" | jq -r '.[0].id // empty')
  [ -n "$ID_CLI" ] && kc DELETE "clients/$ID_CLI" > /dev/null
  rm -f "$IDENTIFIANTS"
  echo "nettoyage du lab iam-03 terminé"
  exit 0
fi

# ─── Retirer tout travail d'un passage précédent ──────────────────────────────
retirer_la_federation
retirer_les_groupes_keycloak
vider_l_annuaire

# ─── Peupler l'annuaire : le résultat du lab 01 ───────────────────────────────
# `openssl rand`, et surtout pas `tr -dc < /dev/urandom | head -c 24` : sous
# `pipefail`, ce pipeline rend un code non nul parce que `head` ferme le tube et
# que `tr` reçoit SIGPIPE. L'affectation réussit, puis `set -e` tue le script.
set +x
SECRET_DES_COMPTES=$(openssl rand -hex 12)
set -x

cat > /tmp/personnes-iam-03.ldif <<LDIF
dn: uid=aline,ou=people,$BASE
objectClass: inetOrgPerson
uid: aline
cn: Aline Dupont
sn: Dupont
mail: aline@formation.lab

dn: uid=bruno,ou=people,$BASE
objectClass: inetOrgPerson
uid: bruno
cn: Bruno Keller
sn: Keller
mail: bruno@formation.lab

dn: uid=chloe,ou=people,$BASE
objectClass: inetOrgPerson
uid: chloe
cn: Chloe Nguyen
sn: Nguyen
mail: chloe@formation.lab
LDIF

set +x
ldapadd -x -H "$LDAP" -D "$ADMIN_DN" -w "$MDP_LDAP" -f /tmp/personnes-iam-03.ldif
for compte in "${PERSONNES[@]}"; do
  ldappasswd -x -H "$LDAP" -D "$ADMIN_DN" -w "$MDP_LDAP" \
    -s "$SECRET_DES_COMPTES" "uid=$compte,ou=people,$BASE"
done
set -x
rm -f /tmp/personnes-iam-03.ldif

cat > /tmp/groupes-iam-03.ldif <<LDIF
dn: cn=devops,ou=groups,$BASE
objectClass: groupOfNames
cn: devops

dn: cn=lecteurs,ou=groups,$BASE
objectClass: groupOfNames
cn: lecteurs
LDIF
set +x
ldapadd -x -H "$LDAP" -D "$ADMIN_DN" -w "$MDP_LDAP" -f /tmp/groupes-iam-03.ldif
set -x
rm -f /tmp/groupes-iam-03.ldif

# Les appartenances passent par l'API : mesuré le 2026-10-16, un `member:` dans
# un LDIF de groupe est accepté puis IGNORÉ par LLDAP, et un `ldapmodify
# add: member` est refusé. C'est ce que le lab 01 fait découvrir.
IDS_GROUPES=$(lldap_api '{"query":"{ groups { id displayName } }"}')
for duo in "devops:${GROUPE_DEVOPS[*]}" "lecteurs:${GROUPE_LECTEURS[*]}"; do
  nom=${duo%%:*}
  membres=${duo#*:}
  gid=$(printf '%s' "$IDS_GROUPES" \
    | jq -r --arg n "$nom" '.data.groups[] | select(.displayName == $n) | .id')
  if [ -z "$gid" ]; then
    echo "ÉCHEC : le groupe $nom n'existe pas après sa création." >&2
    exit 1
  fi
  for membre in $membres; do
    lldap_api "$(jq -nc --arg u "$membre" --argjson g "$gid" \
      '{query:"mutation($u: String!, $g: Int!) { addUserToGroup(userId: $u, groupId: $g) { ok } }", variables:{u:$u, g:$g}}')" \
      > /dev/null
  done
done

# ─── L'outillage de mesure : un client à octroi direct ────────────────────────
kc POST clients "$(jq -nc '{
  clientId:"notes-cli", name:"Client de test", enabled:true,
  publicClient:true, standardFlowEnabled:false,
  directAccessGrantsEnabled:true, serviceAccountsEnabled:false}')" > /dev/null

# ─── Ce que l'apprenant doit savoir pour commencer ────────────────────────────
set +x
{
  echo "# Posé par le setup du lab iam-03. Jetable."
  echo "BASE_DN=${BASE}"
  echo "USERS_DN=ou=people,${BASE}"
  echo "GROUPS_DN=ou=groups,${BASE}"
  echo "ADMIN_DN=${ADMIN_DN}"
  printf 'ADMIN_MOT_DE_PASSE=%s\n' "$MDP_LDAP"
  printf 'COMPTES_MOT_DE_PASSE=%s\n' "$SECRET_DES_COMPTES"
  echo "CLIENT_DE_TEST=notes-cli"
  echo "REALM=${REALM}"
} > "$IDENTIFIANTS"
chown student:docker "$IDENTIFIANTS"
chmod 0640 "$IDENTIFIANTS"

# ─── Contrôler l'état posé, et non le code de retour des commandes ────────────
# Trois comptes et deux groupes doivent être lisibles dans l'annuaire. Sans ce
# contrôle, un lab parti sur un annuaire à moitié rempli échouerait sur un test
# de fédération, et l'apprenant chercherait la cause dans Keycloak.
restants=$(ldapsearch -x -H "$LDAP" -D "$ADMIN_DN" -w "$MDP_LDAP" \
  -b "ou=people,$BASE" -LLL '(objectClass=inetOrgPerson)' dn 2>/dev/null \
  | grep -c '^dn:' || true)
membres_devops=$(ldapsearch -x -H "$LDAP" -D "$ADMIN_DN" -w "$MDP_LDAP" \
  -b "ou=people,$BASE" -LLL "(memberOf=cn=devops,ou=groups,$BASE)" dn 2>/dev/null \
  | grep -c '^dn:' || true)
set -x

if [ "$restants" -lt 4 ]; then
  echo "ÉCHEC : l'annuaire porte $restants compte(s) au lieu de 4 (admin + 3)." >&2
  exit 1
fi
if [ "$membres_devops" -ne 2 ]; then
  echo "ÉCHEC : le groupe devops porte $membres_devops membre(s) au lieu de 2." >&2
  echo "L'API de l'annuaire a-t-elle accepté les appartenances ?" >&2
  exit 1
fi

set +x
echo "Situation posée : annuaire peuplé (3 personnes, 2 groupes), aucune"
echo "fédération déclarée dans le realm $REALM."
echo "Identifiants dans $IDENTIFIANTS"
