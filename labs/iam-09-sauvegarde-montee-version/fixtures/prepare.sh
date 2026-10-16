#!/usr/bin/env bash
# Pose la situation du lab iam-09, et la retire avec `--nettoyer`.
#
# CE QU'IL POSE : une instance « de production » DÉDIÉE, en version N-1, avec
# sa propre base, ses propres ports, son realm, ses comptes, ses clients, et
# des événements qui sont la trace de qui s'est connecté.
#
# POURQUOI DÉDIÉE : le socle des treize autres labs ne doit pas bouger. Monter
# le socle de version le laisserait dans un état que les autres labs n'ont pas
# demandé, et une base migrée ne redescend pas.
#
# CE QU'IL NE FAIT PAS, parce que c'est le travail demandé : aucune
# sauvegarde, aucun export, et l'image reste en N-1. Il RETIRE d'ailleurs les
# sauvegardes et les exports qu'un passage précédent aurait laissés.
#
# La trace va dans /var/log/dsoxlab-prepare.log, avec `set -x`, SUSPENDUE
# autour de chaque secret : ce journal est collecté par `dsoxlab support`.
set -euo pipefail

JOURNAL=/var/log/dsoxlab-prepare.log
exec > >(tee -a "$JOURNAL") 2>&1
set -x

LAB=/opt/iam-lab
PROD=$LAB/prod
SAUVEGARDES=$LAB/sauvegardes
EXPORTS=$LAB/exports
IDENTIFIANTS=$LAB/identifiants-lab.txt
KC_PROD=http://127.0.0.1:8081
REALM=production

#: Les versions du couple. Passées par le setup Ansible, qui les lit dans
#: shared/images.yml. La version DE DÉPART est écrite dans le .env de
#: l'instance : monter de version, c'est changer cette valeur.
#
#: Elles sont EXIGÉES plus bas, et non ici : le mode `--nettoyer` n'en a aucun
#: besoin, et `cleanup.yaml` ne les passe donc pas. Les exiger ici ferait
#: mourir le nettoyage sur une variable qu'il n'utilise pas.
IMAGE_AVANT=${IMAGE_AVANT:-}
IMAGE_APRES=${IMAGE_APRES:-}
IMAGE_PG=${IMAGE_PG:-}
VERSION_AVANT=${VERSION_AVANT:-}
VERSION_APRES=${VERSION_APRES:-}

#: Combien de comptes et de clients l'instance porte. Les tests comptent.
NB_COMPTES=5

arreter_l_instance() {
  if [ -f "$PROD/compose.yaml" ]; then
    (cd "$PROD" && docker compose -f compose.yaml --env-file .env \
      down --volumes --remove-orphans > /dev/null 2>&1) || true
  fi
  # Les conteneurs sont nommés par le projet compose, qu'on retire aussi par
  # son nom : un compose supprimé laisserait sinon des conteneurs orphelins
  # que `docker compose down` ne saurait plus désigner.
  for c in iam-prod-keycloak-1 iam-prod-db-1; do
    docker rm -f "$c" > /dev/null 2>&1 || true
  done
  docker volume rm iam-prod_pgdata > /dev/null 2>&1 || true
  return 0
}

# ─── Mode nettoyage, appelé par cleanup.yaml ──────────────────────────────────
if [ "${1:-}" = "--nettoyer" ]; then
  arreter_l_instance
  rm -f "$PROD/compose.yaml" "$PROD/.env" "$IDENTIFIANTS"
  rm -f "$SAUVEGARDES"/* "$EXPORTS"/* 2>/dev/null || true
  rmdir "$PROD" "$SAUVEGARDES" "$EXPORTS" 2>/dev/null || true
  echo "nettoyage du lab iam-09 terminé"
  exit 0
fi

# ─── À partir d'ici, les versions sont indispensables ─────────────────────────
for variable in IMAGE_AVANT IMAGE_APRES IMAGE_PG VERSION_AVANT VERSION_APRES; do
  if [ -z "${!variable}" ]; then
    echo "ÉCHEC : $variable n'est pas fournie. Le setup la lit dans" >&2
    echo "shared/images.yml et la passe en variable d'environnement." >&2
    exit 1
  fi
done

# ─── Repartir d'une instance neuve ────────────────────────────────────────────
# Une base déjà migrée en version cible rendrait le lab vert avant tout
# travail, et une base migrée ne redescend pas : l'instance est donc recréée.
arreter_l_instance
mkdir -p "$PROD" "$SAUVEGARDES" "$EXPORTS"
rm -f "$SAUVEGARDES"/* "$EXPORTS"/* 2>/dev/null || true

# L'EXPORT EST ÉCRIT PAR LE CONTENEUR, SOUS SON PROPRE COMPTE.
#
# Mesuré le 2026-10-16 : dans l'image de Keycloak, le processus tourne sous
# `keycloak`, UID 1000, et un répertoire monté qui appartient à root lui vaut
# « ERROR: Error during export/import: /exports/<realm>-realm.json (Permission
# denied) » après dix secondes de démarrage. Le répertoire appartient donc à
# `student`, qui porte le même UID 1000 sur cette machine.
#
# Cette coïncidence d'UID n'est pas une garantie : c'est pourquoi le chown est
# explicite plutôt que supposé.
chown student:docker "$SAUVEGARDES" "$EXPORTS"
chmod 0775 "$SAUVEGARDES" "$EXPORTS"

set +x
umask 077
{
  printf 'IMAGE_KEYCLOAK=%s\n' "$IMAGE_AVANT"
  printf 'IMAGE_POSTGRES=%s\n' "$IMAGE_PG"
  printf 'DB_PASSWORD=%s\n' "$(openssl rand -hex 16)"
  printf 'KC_ADMIN=%s\n' "admin-prod"
  printf 'KC_ADMIN_PASSWORD=%s\n' "$(openssl rand -hex 16)"
} > "$PROD/.env"
chown student:docker "$PROD/.env"
chmod 0660 "$PROD/.env"
set -x

cat > "$PROD/compose.yaml" <<'CONF'
# L'instance « de production » du lab iam-09.
#
# LA VERSION N'EST PAS ICI : elle est dans le `.env`, sous IMAGE_KEYCLOAK,
# épinglée par digest. Monter de version, c'est changer cette valeur et
# relancer. Une version écrite en dur dans ce fichier obligerait à le modifier,
# et un fichier de description de service n'est pas l'endroit où vit un choix
# de version.
name: iam-prod

services:
  db:
    image: ${IMAGE_POSTGRES}
    environment:
      POSTGRES_DB: keycloak
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=C.UTF-8"
    volumes:
      # Sur /var/lib/postgresql, et non sur son sous-répertoire /data : voir
      # l'en-tête du compose du socle, qui porte la mesure.
      - pgdata:/var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U keycloak -d keycloak"]
      interval: 5s
      timeout: 5s
      retries: 12
    restart: unless-stopped

  keycloak:
    image: ${IMAGE_KEYCLOAK}
    command: start --optimized=false
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://db:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: ${DB_PASSWORD}
      KC_HTTP_ENABLED: "true"
      KC_HOSTNAME_STRICT: "false"
      KC_HEALTH_ENABLED: "true"
      KC_BOOTSTRAP_ADMIN_USERNAME: ${KC_ADMIN}
      KC_BOOTSTRAP_ADMIN_PASSWORD: ${KC_ADMIN_PASSWORD}
    ports:
      # D'AUTRES PORTS QUE LE SOCLE : 8080 et 9000 lui appartiennent, et deux
      # services sur le même port ne démarrent pas tous les deux.
      - "8081:8080"
      - "9001:9000"
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

volumes:
  pgdata:
CONF
chown student:docker "$PROD/compose.yaml"
chmod 0640 "$PROD/compose.yaml"

(cd "$PROD" && docker compose -f compose.yaml --env-file .env up -d > /dev/null 2>&1)

# ─── Attendre l'instance, et le DIRE si elle ne vient pas ─────────────────────
PRETE=
for _ in $(seq 1 60); do
  CODE=$(curl -sS --max-time 4 -o /dev/null -w '%{http_code}' \
    "$KC_PROD/realms/master/.well-known/openid-configuration" 2>/dev/null || true)
  if [ "$CODE" = "200" ]; then PRETE=oui; break; fi
  sleep 2
done
if [ -z "$PRETE" ]; then
  echo "ÉCHEC : l'instance de production ne répond pas sur $KC_PROD." >&2
  docker logs iam-prod-keycloak-1 2>&1 | tail -15 >&2
  exit 1
fi

set +x
# shellcheck disable=SC1091
. "$PROD/.env"
JETON=$(curl -sS --max-time 20 -X POST \
  "$KC_PROD/realms/master/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  -d "username=$KC_ADMIN" -d "password=$KC_ADMIN_PASSWORD" \
  | jq -r '.access_token // empty')
# Le test qui suit reste dans la zone NON tracée : `set -x` journaliserait
# la valeur du jeton, et ce fichier est collecté par `dsoxlab support`.
if [ -z "$JETON" ]; then
  echo "ÉCHEC : aucun jeton d'administration sur l'instance de production." >&2
  exit 1
fi
set -x

api() {
  set +x
  local m=$1 c=$2 b=${3:-}
  if [ -n "$b" ]; then
    curl -sS --max-time 30 -X "$m" "$KC_PROD/admin/$c" \
      -H "Authorization: Bearer $JETON" -H 'Content-Type: application/json' -d "$b"
  else
    curl -sS --max-time 30 -X "$m" "$KC_PROD/admin/$c" -H "Authorization: Bearer $JETON"
  fi
  set -x
}

# ─── Le realm, ses comptes, ses clients ──────────────────────────────────────
# Les événements sont ACTIVÉS : ils sont la trace de qui s'est connecté, et
# c'est ce qu'un export de realm ne porte pas. Le lab s'appuie dessus.
api POST realms "$(jq -nc --arg r "$REALM" '{
  realm:$r, enabled:true,
  eventsEnabled:true, adminEventsEnabled:true,
  eventsExpiration:0, eventsListeners:["jboss-logging"]}')" > /dev/null

set +x
SECRET_DES_COMPTES=$(openssl rand -hex 12)
set -x

for n in $(seq 1 "$NB_COMPTES"); do
  api POST "realms/$REALM/users" "$(jq -nc --arg u "compte$n" '{
    username:$u, enabled:true, emailVerified:true,
    email:"\($u)@production.lab", firstName:"Compte", lastName:"Numero \($u)"}')" \
    > /dev/null
  identifiant=$(api GET "realms/$REALM/users?username=compte$n&exact=true" \
    | jq -r '.[0].id // empty')
  if [ -z "$identifiant" ]; then
    echo "ÉCHEC : compte$n n'existe pas après sa création." >&2
    exit 1
  fi
  set +x
  api PUT "realms/$REALM/users/$identifiant/reset-password" \
    "$(jq -nc --arg m "$SECRET_DES_COMPTES" \
       '{type:"password", value:$m, temporary:false}')" > /dev/null
  set -x
done

for c in appli-interne appli-publique; do
  api POST "realms/$REALM/clients" "$(jq -nc --arg c "$c" '{
    clientId:$c, enabled:true, publicClient:true,
    directAccessGrantsEnabled:true, standardFlowEnabled:true,
    redirectUris:["http://localhost:9000/*"]}')" > /dev/null
done

# ─── Des événements, qui sont la trace à ne pas perdre ───────────────────────
set +x
for n in 1 2 3; do
  curl -sS --max-time 20 -o /dev/null -X POST \
    "$KC_PROD/realms/$REALM/protocol/openid-connect/token" \
    -d grant_type=password -d client_id=appli-publique \
    -d "username=compte$n" -d "password=$SECRET_DES_COMPTES" || true
done
set -x
sleep 2

# ─── Ce que l'apprenant doit savoir pour commencer ───────────────────────────
set +x
{
  echo "# Posé par le setup du lab iam-09. Jetable."
  echo "REALM=${REALM}"
  echo "URL_PROD=${KC_PROD}"
  echo "REPERTOIRE_PROD=${PROD}"
  echo "ENV_PROD=${PROD}/.env"
  echo "COMPOSE_PROD=${PROD}/compose.yaml"
  printf 'MOT_DE_PASSE=%s\n' "$SECRET_DES_COMPTES"
  echo "NB_COMPTES_ATTENDUS=${NB_COMPTES}"
  echo "VERSION_DE_DEPART=${VERSION_AVANT}"
  echo "VERSION_CIBLE=${VERSION_APRES}"
  echo "IMAGE_CIBLE=${IMAGE_APRES}"
  echo "REPERTOIRE_SAUVEGARDES=${SAUVEGARDES}"
  echo "REPERTOIRE_EXPORTS=${EXPORTS}"
  echo "CONTENEUR_KEYCLOAK=iam-prod-keycloak-1"
  echo "CONTENEUR_BASE=iam-prod-db-1"
} > "$IDENTIFIANTS"
chown student:docker "$IDENTIFIANTS"
chmod 0640 "$IDENTIFIANTS"
set -x

# ─── Contrôler l'état posé ───────────────────────────────────────────────────
# Sans ces contrôles, un lab parti d'un travail déjà fait serait vert avant
# d'avoir commencé.
set +x
VERSION_LUE=$(curl -sS --max-time 20 "$KC_PROD/admin/serverinfo" \
  -H "Authorization: Bearer $JETON" | jq -r '.systemInfo.version // empty')
set -x
COMPTES=$(api GET "realms/$REALM/users?max=100" | jq 'length')
EVENEMENTS=$(api GET "realms/$REALM/events?max=50" | jq 'length')
NB_SAUVEGARDES=$(find "$SAUVEGARDES" -type f | wc -l)
NB_EXPORTS=$(find "$EXPORTS" -type f | wc -l)

if [ "$VERSION_LUE" != "$VERSION_AVANT" ] || [ "$COMPTES" -ne "$NB_COMPTES" ] \
   || [ "$EVENEMENTS" -lt 1 ] || [ "$NB_SAUVEGARDES" -ne 0 ] \
   || [ "$NB_EXPORTS" -ne 0 ]; then
  echo "ÉCHEC : la situation de départ n'est pas celle attendue." >&2
  echo "version=$VERSION_LUE (attendu $VERSION_AVANT) comptes=$COMPTES" >&2
  echo "evenements=$EVENEMENTS (au moins 1) sauvegardes=$NB_SAUVEGARDES (0)" >&2
  echo "exports=$NB_EXPORTS (0)" >&2
  exit 1
fi

set +x
echo "Situation posée : instance de production en $VERSION_AVANT sur $KC_PROD,"
echo "realm $REALM avec $COMPTES comptes, 2 clients, $EVENEMENTS événements,"
echo "aucune sauvegarde et aucun export."
echo "Identifiants dans $IDENTIFIANTS"
