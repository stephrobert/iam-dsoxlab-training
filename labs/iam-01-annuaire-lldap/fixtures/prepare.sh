#!/usr/bin/env bash
# Pose la situation du lab iam-01, et la retire avec `--nettoyer`.
#
# CE QUE CE SCRIPT NE FAIT PAS : créer les comptes ni les groupes. C'est le
# travail demandé.
#
# CE QU'IL FAIT : retirer tout ce qu'un passage précédent aurait laissé dans
# l'annuaire, et écrire où lire le DN de base et le compte d'administration.
#
# POURQUOI L'ANNUAIRE EST DÉJÀ DEBOUT
#
# LLDAP fait partie du socle, parce que cinq labs suivants le lisent. Le
# démarrer ici ferait doublon avec `iam-02`, qui enseigne déjà à monter un
# service en Compose. Le sujet propre de ce lab est l'ORGANISATION de
# l'annuaire, qui est la compétence qu'un fournisseur d'identité suppose
# acquise.
#
# La trace va dans /var/log/dsoxlab-prepare.log, avec `set -x`.
set -euo pipefail

JOURNAL=/var/log/dsoxlab-prepare.log
exec > >(tee -a "$JOURNAL") 2>&1
set -x

SOCLE_ENV=/opt/socle-iam/.env
IDENTIFIANTS=/opt/iam-lab/identifiants-lab.txt
WEB=http://127.0.0.1:17170
LDAP=ldap://127.0.0.1:3890

if [ ! -r "$SOCLE_ENV" ]; then
  echo "ÉCHEC : $SOCLE_ENV est absent ou illisible. Le socle IAM n'est pas" >&2
  echo "installé, ou ce script tourne sous un compte hors du groupe docker." >&2
  exit 1
fi

# `cut -d= -f2-`, ET PAS `-f2`.
#
# Mesuré le 2026-10-16 : le DN de base vaut `dc=formation,dc=lab`, et
# `cut -d= -f2` le coupe au premier `=` en rendant `dc`. Toutes les requêtes
# LDAP échouaient alors sur « Naming violation (64) : Missing DN value », ce qui
# désigne la requête et non la variable qui l'a fabriquée.
BASE=$(grep '^LLDAP_BASE_DN=' "$SOCLE_ENV" | cut -d= -f2-)
# LA TRACE S'ARRÊTE AUTOUR DU SECRET, ET ELLE REPREND APRÈS.
#
# `/var/log/dsoxlab-prepare.log` est collecté par `dsoxlab support`,
# qui sert à demander de l'aide : un rapport partagé ne doit pas porter
# le mot de passe d'administration de l'annuaire. Mesuré le
# 2026-10-16, il y figurait en clair, répété à chaque commande `ldap*`
# que `set -x` déroulait.
#
# Le reste du script reste tracé : c'est lui qui sert à comprendre un
# échec.
set +x
MDP_ADMIN=$(grep '^LLDAP_ADMIN_PASSWORD=' "$SOCLE_ENV" | cut -d= -f2-)
set -x
ADMIN_DN="uid=admin,ou=people,$BASE"

#: Les comptes et les groupes que l'apprenant doit créer, donc que l'on retire.
COMPTES_DU_TRAVAIL=(aline bruno chloe)
GROUPES_DU_TRAVAIL=(devops lecteurs)

jeton_lldap() {
  # Hors trace : le corps de la requête porte le mot de passe.
  set +x
  curl -sS --max-time 20 -X POST "$WEB/auth/simple/login" \
    -H 'Content-Type: application/json' \
    -d "$(jq -nc --arg m "$MDP_ADMIN" '{username:"admin", password:$m}')" \
    | jq -r '.token // empty'
  set -x
}

retirer_les_groupes() {
  # Par l'API, parce que `deleteGroup` prend l'identifiant NUMÉRIQUE du groupe,
  # que seule l'API connaît. Un `ldapdelete` fonctionnerait aussi, mais mieux
  # vaut une seule voie pour une seule chose.
  #
  # Hors trace : le jeton de session passe en en-tête, et `set -x` l'écrirait
  # dans un journal que `dsoxlab support` collecte. Un jeton expire, mais il
  # ouvre l'annuaire entier d'ici là.
  local jeton=$1 identifiants
  set +x
  identifiants=$(curl -sS --max-time 20 -X POST "$WEB/api/graphql" \
    -H "Authorization: Bearer $jeton" -H 'Content-Type: application/json' \
    -d '{"query":"{ groups { id displayName } }"}' \
    | jq -r --argjson noms "$(printf '%s\n' "${GROUPES_DU_TRAVAIL[@]}" | jq -R . | jq -s .)" \
      '.data.groups[] | select(.displayName as $n | $noms | index($n)) | .id')
  for identifiant in $identifiants; do
    curl -sS --max-time 20 -o /dev/null -X POST "$WEB/api/graphql" \
      -H "Authorization: Bearer $jeton" -H 'Content-Type: application/json' \
      -d "$(jq -nc --argjson g "$identifiant" \
        '{query:"mutation($g: Int!) { deleteGroup(groupId: $g) { ok } }", variables:{g:$g}}')"
  done
  set -x
}

retirer_les_comptes() {
  # Hors trace : `-w "$MDP_ADMIN"` serait affiché avec sa valeur.
  local compte
  set +x
  for compte in "${COMPTES_DU_TRAVAIL[@]}"; do
    ldapdelete -x -H "$LDAP" -D "$ADMIN_DN" -w "$MDP_ADMIN" \
      "uid=$compte,ou=people,$BASE" 2>/dev/null || true
  done
  set -x
}

JETON=$(jeton_lldap)
if [ -z "$JETON" ]; then
  echo "ÉCHEC : aucun jeton de l'API LLDAP. L'annuaire répond-il sur $WEB ?" >&2
  exit 1
fi

# ─── Mode nettoyage, appelé par cleanup.yaml ──────────────────────────────────
if [ "${1:-}" = "--nettoyer" ]; then
  retirer_les_groupes "$JETON"
  retirer_les_comptes
  rm -f "$IDENTIFIANTS"
  echo "nettoyage du lab iam-01 terminé"
  exit 0
fi

# ─── Retirer tout travail d'un passage précédent ──────────────────────────────
# Les groupes AVANT les comptes : un groupe dont les membres ont disparu reste,
# et le test d'appartenance serait alors vert sur un groupe vide.
retirer_les_groupes "$JETON"
retirer_les_comptes

# ─── Ce que l'apprenant doit savoir pour commencer ────────────────────────────
# Le DN de base et le compte d'administration. Le mot de passe est celui que le
# socle a tiré au hasard : il n'est pas dans le dépôt, et il est régénéré à
# chaque installation du socle.
set +x
{
  echo "# Posé par le setup du lab iam-01. Jetable."
  echo "BASE_DN=${BASE}"
  echo "ADMIN_DN=${ADMIN_DN}"
  printf 'ADMIN_MOT_DE_PASSE=%s\n' "$MDP_ADMIN"
  echo "LDAP_URL=${LDAP}"
  echo "WEB_URL=${WEB}"
} > "$IDENTIFIANTS"
chown student:docker "$IDENTIFIANTS"
chmod 0640 "$IDENTIFIANTS"
set -x

# ─── L'annuaire doit répondre, sinon le lab n'est pas jouable ─────────────────
# Sur l'ÉTAT, pas sur le fait que le conteneur existe : un LLDAP qui démarre
# n'est pas un LLDAP qui sert, et l'apprenant verrait des refus de connexion
# qu'il prendrait pour une erreur de sa requête.
set +x
if ! ldapwhoami -x -H "$LDAP" -D "$ADMIN_DN" -w "$MDP_ADMIN" > /dev/null 2>&1; then
  echo "ÉCHEC : l'annuaire ne répond pas sur $LDAP avec le compte du socle." >&2
  docker logs --tail 20 socle-iam-lldap-1 >&2 2>&1 || true
  exit 1
fi
set -x

set +x
echo "Situation posée : annuaire vide sous ou=people et ou=groups (hors admin)."
echo "DN de base : $BASE"
echo "Identifiants dans $IDENTIFIANTS"
