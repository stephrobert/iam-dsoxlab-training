#!/usr/bin/env bash
# Pose la situation du lab iam-08, et la retire avec `--nettoyer`.
#
# CE QU'IL POSE : l'annuaire peuplé, la fédération en lecture seule (le résultat
# du lab 03), quatre comptes dans deux groupes, et une SESSION ACTIVE pour la
# personne qui part, avec son jeton de rafraîchissement déposé sur la machine.
#
# POURQUOI UNE SESSION ACTIVE EST POSÉE
#
# Sans elle, le lab se réduirait à cocher une case. Mesuré le 2026-10-16 : une
# session SURVIT à la désactivation du compte. C'est le geste que tout le monde
# oublie, et il ne se voit pas : la fiche du compte dit « désactivé », et la
# session continue.
#
# CE QUE CE SCRIPT NE FAIT PAS : désactiver le compte, fermer ses sessions,
# retirer ses groupes, ni écrire la revue. C'est le travail demandé.
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
JETONS=/opt/iam-lab/jetons-de-la-session.txt
REVUE=/opt/iam-lab/revue-des-acces.json
LDAP=ldap://127.0.0.1:3890
WEB=http://127.0.0.1:17170

#: Qui part, et qui reste.
QUI_PART=morgane
QUI_RESTE=(aline bruno chloe)

if [ ! -r "$SOCLE_ENV" ]; then
  echo "ÉCHEC : $SOCLE_ENV est absent ou illisible. Le socle IAM n'est pas" >&2
  echo "installé, ou ce script tourne sous un compte hors du groupe docker." >&2
  exit 1
fi

# `cut -d= -f2-`, et pas `-f2` : le DN de base contient le séparateur.
BASE=$(grep '^LLDAP_BASE_DN=' "$SOCLE_ENV" | cut -d= -f2-)
ADMIN_DN="uid=admin,ou=people,$BASE"

set +x
MDP_LDAP=$(grep '^LLDAP_ADMIN_PASSWORD=' "$SOCLE_ENV" | cut -d= -f2-)
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

jeton_lldap() {
  set +x
  curl -sS --max-time 20 -X POST "$WEB/auth/simple/login" \
    -H 'Content-Type: application/json' \
    -d "$(jq -nc --arg m "$MDP_LDAP" '{username:"admin", password:$m}')" \
    | jq -r '.token // empty'
  set -x
}

lldap_api() {
  set +x
  curl -sS --max-time 20 -X POST "$WEB/api/graphql" \
    -H "Authorization: Bearer $JETON_LDAP" -H 'Content-Type: application/json' \
    -d "$1"
  set -x
}

vider_le_realm() {
  local id
  for id in $(admin GET "realms/$REALM/components?parent=$ID_REALM&type=org.keycloak.storage.UserStorageProvider" \
              | jq -r '.[].id'); do
    admin DELETE "realms/$REALM/components/$id" > /dev/null
  done
  for id in $(admin GET "realms/$REALM/groups" | jq -r '.[].id'); do
    admin DELETE "realms/$REALM/groups/$id" > /dev/null
  done
  for id in $(admin GET "realms/$REALM/users?max=200" | jq -r '.[].id'); do
    admin DELETE "realms/$REALM/users/$id" > /dev/null
  done
  id=$(admin GET "realms/$REALM/clients?clientId=appli-notes" \
    | jq -r '.[0].id // empty')
  [ -n "$id" ] && admin DELETE "realms/$REALM/clients/$id" > /dev/null
  return 0
}

vider_l_annuaire() {
  local compte groupes id
  set +x
  for compte in "$QUI_PART" "${QUI_RESTE[@]}"; do
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

ID_REALM=$(admin GET "realms/$REALM" | jq -r .id)
JETON_LDAP=$(jeton_lldap)
if [ -z "$JETON_LDAP" ]; then
  echo "ÉCHEC : aucun jeton de l'API LLDAP. L'annuaire répond-il ?" >&2
  exit 1
fi

# ─── Mode nettoyage, appelé par cleanup.yaml ──────────────────────────────────
if [ "${1:-}" = "--nettoyer" ]; then
  vider_le_realm
  vider_l_annuaire
  rm -f "$IDENTIFIANTS" "$JETONS" "$REVUE"
  echo "nettoyage du lab iam-08 terminé"
  exit 0
fi

# ─── Retirer tout travail d'un passage précédent ──────────────────────────────
vider_le_realm
vider_l_annuaire
rm -f "$REVUE"

# ─── Peupler l'annuaire : quatre personnes, deux groupes ──────────────────────
set +x
SECRET_DES_COMPTES=$(openssl rand -hex 12)
set -x

cat > /tmp/personnes-iam-08.ldif <<LDIF
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

dn: uid=$QUI_PART,ou=people,$BASE
objectClass: inetOrgPerson
uid: $QUI_PART
cn: Morgane Leroy
sn: Leroy
mail: $QUI_PART@formation.lab
LDIF

set +x
ldapadd -x -H "$LDAP" -D "$ADMIN_DN" -w "$MDP_LDAP" -f /tmp/personnes-iam-08.ldif
for compte in "$QUI_PART" "${QUI_RESTE[@]}"; do
  ldappasswd -x -H "$LDAP" -D "$ADMIN_DN" -w "$MDP_LDAP" \
    -s "$SECRET_DES_COMPTES" "uid=$compte,ou=people,$BASE"
done
set -x
rm -f /tmp/personnes-iam-08.ldif

cat > /tmp/groupes-iam-08.ldif <<LDIF
dn: cn=devops,ou=groups,$BASE
objectClass: groupOfNames
cn: devops

dn: cn=lecteurs,ou=groups,$BASE
objectClass: groupOfNames
cn: lecteurs
LDIF
set +x
ldapadd -x -H "$LDAP" -D "$ADMIN_DN" -w "$MDP_LDAP" -f /tmp/groupes-iam-08.ldif
set -x
rm -f /tmp/groupes-iam-08.ldif

# Les appartenances par l'API : mesuré le 2026-10-16, un `member:` dans un LDIF
# de groupe est accepté puis IGNORÉ par LLDAP.
IDS_GROUPES=$(lldap_api '{"query":"{ groups { id displayName } }"}')
for duo in "devops:aline bruno $QUI_PART" "lecteurs:bruno chloe"; do
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

# ─── La fédération en lecture seule, et son mappeur de groupes ────────────────
admin POST "realms/$REALM/components" "$(jq -nc \
  --arg base "$BASE" --arg dn "$ADMIN_DN" --arg mdp "$MDP_LDAP" \
  --arg parent "$ID_REALM" '{
  name:"annuaire-lldap", providerId:"ldap",
  providerType:"org.keycloak.storage.UserStorageProvider", parentId:$parent,
  config:{
    enabled:["true"], priority:["0"], importEnabled:["true"],
    editMode:["READ_ONLY"], syncRegistrations:["false"], vendor:["other"],
    usernameLDAPAttribute:["uid"], rdnLDAPAttribute:["uid"],
    uuidLDAPAttribute:["entryUUID"], userObjectClasses:["inetOrgPerson"],
    connectionUrl:["ldap://lldap:3890"],
    usersDn:[("ou=people," + $base)], authType:["simple"],
    bindDn:[$dn], bindCredential:[$mdp],
    searchScope:["1"], pagination:["true"]}}')" > /dev/null

ID_FED=$(admin GET "realms/$REALM/components?parent=$ID_REALM&type=org.keycloak.storage.UserStorageProvider" \
  | jq -r '.[0].id // empty')
if [ -z "$ID_FED" ]; then
  echo "ÉCHEC : la fédération n'existe pas après sa création." >&2
  exit 1
fi

admin POST "realms/$REALM/components" "$(jq -nc \
  --arg base "$BASE" --arg parent "$ID_FED" '{
  name:"groupes", providerId:"group-ldap-mapper",
  providerType:"org.keycloak.storage.ldap.mappers.LDAPStorageMapper",
  parentId:$parent,
  config:{
    "groups.dn":[("ou=groups," + $base)],
    "group.name.ldap.attribute":["cn"],
    "group.object.classes":["groupOfNames"],
    "membership.ldap.attribute":["member"],
    "membership.attribute.type":["DN"],
    "membership.user.ldap.attribute":["uid"],
    "mode":["READ_ONLY"],
    "user.roles.retrieve.strategy":["LOAD_GROUPS_BY_MEMBER_ATTRIBUTE"],
    "preserve.group.inheritance":["false"],
    "ignore.missing.groups":["false"],
    "memberof.ldap.attribute":["memberOf"],
    "drop.non.existing.groups.during.sync":["false"]}}')" > /dev/null

ID_MAPPEUR=$(admin GET "realms/$REALM/components?parent=$ID_FED&type=org.keycloak.storage.ldap.mappers.LDAPStorageMapper" \
  | jq -r '.[] | select(.name=="groupes") | .id')

curl -sS --max-time 120 -o /dev/null -X POST \
  "$KC/admin/realms/$REALM/user-storage/$ID_FED/sync?action=triggerFullSync" \
  -H "Authorization: Bearer $JETON"
curl -sS --max-time 120 -o /dev/null -X POST \
  "$KC/admin/realms/$REALM/user-storage/$ID_FED/mappers/$ID_MAPPEUR/sync?direction=fedToKeycloak" \
  -H "Authorization: Bearer $JETON"

# ─── Un rôle accordé DIRECTEMENT, hors groupe ─────────────────────────────────
# C'est ce que les revues oublient : un rôle attaché au compte, et non à un
# groupe, n'apparaît dans aucune liste de groupes. Celui-ci devra figurer dans
# la revue, et disparaître avec le départ.
admin POST "realms/$REALM/roles" '{"name":"acces-exceptionnel-sauvegardes"}' > /dev/null
LE_ROLE=$(admin GET "realms/$REALM/roles/acces-exceptionnel-sauvegardes")
ID_QUI_PART=$(admin GET "realms/$REALM/users?username=$QUI_PART&exact=true" \
  | jq -r '.[0].id // empty')
if [ -z "$ID_QUI_PART" ]; then
  echo "ÉCHEC : $QUI_PART n'est pas connu du realm après la synchronisation." >&2
  echo "L'adresse de connexion de la fédération est-elle joignable depuis le" >&2
  echo "conteneur de Keycloak ?" >&2
  exit 1
fi
admin POST "realms/$REALM/users/$ID_QUI_PART/role-mappings/realm" \
  "$(printf '[%s]' "$LE_ROLE")" > /dev/null

# ─── Un client, et une SESSION ACTIVE pour la personne qui part ───────────────
# L'octroi direct est ouvert sur ce client : c'est de l'outillage, qui permet de
# poser une session sans navigateur. Le lab 04 apprend justement à le fermer.
admin POST "realms/$REALM/clients" "$(jq -nc '{
  clientId:"appli-notes", name:"Application notes", enabled:true,
  publicClient:true, standardFlowEnabled:true, implicitFlowEnabled:false,
  directAccessGrantsEnabled:true, serviceAccountsEnabled:false,
  redirectUris:["http://127.0.0.1:9080/callback"],
  webOrigins:["http://127.0.0.1:9080"]}')" > /dev/null

set +x
REPONSE=$(curl -sS --max-time 20 -X POST \
  "$KC/realms/$REALM/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=appli-notes -d scope=openid \
  -d "username=$QUI_PART" -d "password=$SECRET_DES_COMPTES")
ACCES=$(printf '%s' "$REPONSE" | jq -r '.access_token // empty')
RAFRAICHIR=$(printf '%s' "$REPONSE" | jq -r '.refresh_token // empty')
# Le contrôle reste HORS TRACE : `set -x` afficherait les deux jetons en entier
# dans /var/log/dsoxlab-prepare.log, que `dsoxlab support` collecte. Un jeton de
# rafraîchissement vaut une session complète.
if [ -z "$ACCES" ] || [ -z "$RAFRAICHIR" ]; then
  set -x
  echo "ÉCHEC : aucune session n'a pu être ouverte pour $QUI_PART." >&2
  exit 1
fi
set -x

set +x
{
  echo "# Jetons de la session ouverte par le setup pour $QUI_PART."
  echo "# Ils servent aux tests : ne les modifiez pas."
  printf 'ACCESS_TOKEN=%s\n' "$ACCES"
  printf 'REFRESH_TOKEN=%s\n' "$RAFRAICHIR"
} > "$JETONS"
chown student:docker "$JETONS"
chmod 0640 "$JETONS"

{
  echo "# Posé par le setup du lab iam-08. Jetable."
  echo "REALM=${REALM}"
  echo "QUI_PART=${QUI_PART}"
  echo "QUI_RESTE=${QUI_RESTE[*]}"
  printf 'MOT_DE_PASSE=%s\n' "$SECRET_DES_COMPTES"
  echo "ROLE_DIRECT=acces-exceptionnel-sauvegardes"
  echo "FICHIER_DE_REVUE=${REVUE}"
  echo "JETONS_DE_LA_SESSION=${JETONS}"
} > "$IDENTIFIANTS"
chown student:docker "$IDENTIFIANTS"
chmod 0640 "$IDENTIFIANTS"
set -x

# ─── Contrôler l'état posé ────────────────────────────────────────────────────
# Le compte doit être ACTIF, avec une session OUVERTE et deux groupes. Sans ce
# contrôle, un lab parti d'un état déjà nettoyé serait vert avant tout travail.
SESSIONS=$(admin GET "realms/$REALM/users/$ID_QUI_PART/sessions" | jq 'length')
GROUPES=$(admin GET "realms/$REALM/users/$ID_QUI_PART/groups" | jq 'length')
ACTIF=$(admin GET "realms/$REALM/users/$ID_QUI_PART" | jq -r '.enabled')
if [ "$ACTIF" != "true" ] || [ "$SESSIONS" -lt 1 ] || [ "$GROUPES" -lt 1 ]; then
  echo "ÉCHEC : la situation de départ n'est pas celle attendue." >&2
  echo "actif=$ACTIF sessions=$SESSIONS groupes=$GROUPES" >&2
  exit 1
fi

set +x
echo "Situation posée : $QUI_PART est actif, dans $GROUPES groupe(s), avec"
echo "$SESSIONS session(s) ouverte(s) et un rôle accordé directement."
echo "Identifiants dans $IDENTIFIANTS"
