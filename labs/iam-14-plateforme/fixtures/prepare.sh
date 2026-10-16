#!/usr/bin/env bash
# Pose la situation du lab iam-14, et la retire avec `--nettoyer`.
#
# CE QU'IL POSE, qui est un PRÉREQUIS et non le sujet :
#   - k3d et kubectl, épinglés, et l'image du cluster pré-tirée ;
#   - un accès TLS devant Keycloak, parce qu'un apiserver REFUSE un issuer en
#     http (mesuré le 2026-10-16, message exact dans shared/images.yml) ;
#   - deux groupes et deux comptes dans le realm ;
#   - l'outil de plateforme DEBOUT mais NON BRANCHÉ, avec un fichier
#     d'environnement à compléter et un script pour le redémarrer.
#
# CE QU'IL NE FAIT PAS, parce que c'est le travail demandé :
#   - créer le cluster, ni écrire sa configuration d'authentification ;
#   - déclarer le client `kubernetes` ni ses deux mappeurs ;
#   - lier quoi que ce soit en RBAC ;
#   - brancher l'outil sur l'IdP.
#
# La trace va dans /var/log/dsoxlab-prepare.log, avec `set -x`, SUSPENDUE
# autour de chaque secret : ce journal est collecté par `dsoxlab support`.
set -euo pipefail

JOURNAL=/var/log/dsoxlab-prepare.log
exec > >(tee -a "$JOURNAL") 2>&1
set -x

KC=http://127.0.0.1:8080
REALM=formation
SOCLE=/opt/socle-iam
SOCLE_ENV=$SOCLE/.env
LAB=/opt/iam-lab
TLS=$LAB/tls
OUTILS=$LAB/outils
IDENTIFIANTS=$LAB/identifiants-lab.txt
CONF_AUTH=/etc/k3d-oidc
GRAFANA_ENV=$LAB/grafana.env

#: Le cluster que l'apprenant doit créer. Les tests le cherchent sous ce nom.
CLUSTER=lab-iam
#: Les groupes du lab, et les comptes qui les portent.
GROUPE_DEVOPS=devops
GROUPE_LECTEURS=lecteurs
COMPTE_DEVOPS=dev-kube
COMPTE_LECTEUR=lecteur-kube
#: Le namespace où l'équipe devops doit pouvoir écrire, et pas ailleurs.
NAMESPACE=applications

# Versions passées par le setup Ansible, qui les lit dans shared/images.yml.
# Un défaut est fourni pour qu'un appel à la main reste possible, mais la
# valeur qui fait foi vit dans images.yml : une version recopiée finit toujours
# par diverger.
K3D_VERSION=${K3D_VERSION:-v5.9.0}
KUBECTL_VERSION=${KUBECTL_VERSION:-v1.37.1}
IMAGE_K3S=${IMAGE_K3S:-docker.io/rancher/k3s:v1.37.1-k3s1}
#: Le nom SANS digest, sous lequel l'image est retaguée localement. `docker
#: pull nom:tag@digest` résout par digest et ne pose PAS le tag en local :
#: l'apprenant qui nomme son image par son tag relancerait un tirage. Mesuré.
TAG_K3S=${TAG_K3S:-rancher/k3s:v1.37.1-k3s1}
IMAGE_GRAFANA=${IMAGE_GRAFANA:-docker.io/grafana/grafana:12.3.1}
IMAGE_NGINX=${IMAGE_NGINX:-docker.io/library/nginx:1.29-alpine}

if [ ! -r "$SOCLE_ENV" ]; then
  echo "ÉCHEC : $SOCLE_ENV est absent ou illisible. Le socle IAM n'est pas" >&2
  echo "installé, ou ce script tourne sous un compte hors du groupe docker." >&2
  exit 1
fi

IP=$(ip -4 -o addr show scope global | awk '{print $4}' | cut -d/ -f1 | head -1)
if [ -z "$IP" ]; then
  echo "ÉCHEC : aucune adresse IPv4 globale sur cette machine." >&2
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

retirer_le_travail() {
  # Retire ce que l'APPRENANT a pu poser, pour que le lab reparte du même
  # point. Un lab qui démarre sur le travail du passage précédent est vert
  # avant d'avoir commencé.
  local id nom
  k3d cluster delete "$CLUSTER" > /dev/null 2>&1 || true
  # Suppression CIBLÉE, et non récursive : `rm -rf` sur un chemin tenu
  # par une variable est le geste qui efface autre chose le jour où la
  # variable est vide.
  rm -f "$CONF_AUTH/auth.yaml"
  rmdir "$CONF_AUTH" 2>/dev/null || true
  for nom in kubernetes grafana; do
    id=$(admin GET "realms/$REALM/clients?clientId=$nom" | jq -r '.[0].id // empty')
    [ -n "$id" ] && admin DELETE "realms/$REALM/clients/$id" > /dev/null
  done
  return 0
}

retirer_les_objets() {
  local id nom
  for nom in "$COMPTE_DEVOPS" "$COMPTE_LECTEUR"; do
    id=$(admin GET "realms/$REALM/users?username=$nom&exact=true" \
      | jq -r '.[0].id // empty')
    [ -n "$id" ] && admin DELETE "realms/$REALM/users/$id" > /dev/null
  done
  for nom in "$GROUPE_DEVOPS" "$GROUPE_LECTEURS"; do
    id=$(admin GET "realms/$REALM/groups" \
      | jq -r --arg n "$nom" '.[] | select(.name == $n) | .id')
    [ -n "$id" ] && admin DELETE "realms/$REALM/groups/$id" > /dev/null
  done
  return 0
}

retirer_l_outil() {
  docker rm -f grafana-lab > /dev/null 2>&1 || true
  rm -f "$GRAFANA_ENV" "$OUTILS/redemarrer-grafana.sh"
  return 0
}

refermer_l_acces_tls() {
  # Rend le socle à son état nu : plus de proxy, et Keycloak sans
  # KC_PROXY_HEADERS. `--remove-orphans` retire le service que l'override
  # ajoutait, sans quoi le proxy survivrait au nettoyage.
  rm -f "$SOCLE/compose-tls.yaml"
  if [ -f "$SOCLE/compose.yaml" ]; then
    (cd "$SOCLE" && docker compose -f compose.yaml --env-file .env \
      up -d --remove-orphans > /dev/null 2>&1) || true
  fi
  rm -f "$TLS/idp.crt" "$TLS/idp.key" "$TLS/proxy.conf"
  rmdir "$TLS" 2>/dev/null || true
  return 0
}

# ─── Mode nettoyage, appelé par cleanup.yaml ──────────────────────────────────
if [ "${1:-}" = "--nettoyer" ]; then
  retirer_le_travail
  retirer_les_objets
  retirer_l_outil
  refermer_l_acces_tls
  rm -f "$IDENTIFIANTS"
  echo "nettoyage du lab iam-14 terminé"
  exit 0
fi

# ─── Retirer tout travail d'un passage précédent ──────────────────────────────
retirer_le_travail
retirer_les_objets
retirer_l_outil

# ─── 1. Les outils du cluster, épinglés ───────────────────────────────────────
mkdir -p "$OUTILS" "$TLS"
if ! command -v k3d > /dev/null 2>&1 \
   || [ "$(k3d version | awk '/k3d version/{print $3}')" != "$K3D_VERSION" ]; then
  curl -sSL --max-time 180 \
    "https://github.com/k3d-io/k3d/releases/download/$K3D_VERSION/k3d-linux-amd64" \
    -o /usr/local/bin/k3d
  chmod 0755 /usr/local/bin/k3d
fi
if ! command -v kubectl > /dev/null 2>&1 \
   || [ "$(kubectl version --client -o json | jq -r .clientVersion.gitVersion)" \
        != "$KUBECTL_VERSION" ]; then
  curl -sSL --max-time 180 \
    "https://dl.k8s.io/release/$KUBECTL_VERSION/bin/linux/amd64/kubectl" \
    -o /usr/local/bin/kubectl
  chmod 0755 /usr/local/bin/kubectl
fi
# L'image est tirée MAINTENANT : un apprenant qui crée son cluster attendrait
# sinon 250 Mo de téléchargement en croyant que son cluster est en panne.
docker pull --quiet "$IMAGE_K3S" > /dev/null
docker tag "$IMAGE_K3S" "$TAG_K3S"
docker pull --quiet "$IMAGE_NGINX" > /dev/null
docker pull --quiet "$IMAGE_GRAFANA" > /dev/null

# ─── 2. L'accès TLS devant Keycloak ───────────────────────────────────────────
# POURQUOI : l'apiserver refuse un issuer en http, mot pour mot « URL scheme
# must be https ». Sans cet accès, le lab est injouable, et ce n'est pas son
# sujet : il est donc posé ici.
if [ ! -f "$TLS/idp.crt" ]; then
  openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
    -keyout "$TLS/idp.key" -out "$TLS/idp.crt" \
    -subj "/CN=idp.lab" \
    -addext "subjectAltName=DNS:idp.lab,IP:$IP" 2>/dev/null
fi
chmod 0644 "$TLS/idp.crt"
chmod 0640 "$TLS/idp.key"

cat > "$TLS/proxy.conf" <<'CONF'
server {
  listen 8443 ssl;
  http2 on;
  server_name idp.lab;
  ssl_certificate     /tls/idp.crt;
  ssl_certificate_key /tls/idp.key;
  location / {
    proxy_pass http://keycloak:8080;
    proxy_set_header Host              $host:8443;
    proxy_set_header X-Forwarded-For   $remote_addr;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header X-Forwarded-Host  $host;
    proxy_set_header X-Forwarded-Port  8443;
  }
}
CONF

cat > "$SOCLE/compose-tls.yaml" <<CONF
# Ajouté par le setup du lab iam-14, et retiré par son nettoyage.
#
# Le socle reste en HTTP sur 8080 : cet override AJOUTE une porte TLS, il n'en
# ferme aucune. Keycloak calcule son issuer depuis la requête, donc les deux
# portes annoncent chacune le sien, et les autres labs ne voient aucun
# changement.
services:
  keycloak:
    environment:
      # SANS CECI, l'issuer reste en http derrière le proxy, et le cluster
      # refuse le jeton sans rien dire d'utile. Mesuré le 2026-10-16.
      KC_PROXY_HEADERS: xforwarded
  proxy-tls:
    image: $IMAGE_NGINX
    volumes:
      - $TLS/proxy.conf:/etc/nginx/conf.d/default.conf:ro
      - $TLS:/tls:ro
    ports:
      - "8443:8443"
    depends_on:
      - keycloak
    restart: unless-stopped
CONF

(cd "$SOCLE" && docker compose -f compose.yaml -f compose-tls.yaml \
  --env-file .env up -d > /dev/null 2>&1)

# Attendre que la porte TLS réponde, et le DIRE si elle ne répond pas.
ISSUER=""
for _ in $(seq 1 45); do
  # `|| true` N'EST PAS DÉCORATIF : pendant que Keycloak redémarre pour prendre
  # KC_PROXY_HEADERS, le proxy rend 502, `jq` sort en 5 sur cette page, et
  # l'affectation prend le code du pipeline. Avec `set -e`, le script mourrait
  # au PREMIER tour au lieu d'attendre, et le message accuserait la porte TLS
  # de ne pas répondre alors qu'elle n'a pas encore eu le temps.
  ISSUER=$(curl -sS --max-time 5 --cacert "$TLS/idp.crt" \
    --resolve "idp.lab:8443:127.0.0.1" \
    "https://idp.lab:8443/realms/$REALM/.well-known/openid-configuration" \
    2>/dev/null | jq -r '.issuer // empty' 2>/dev/null || true)
  [ -n "$ISSUER" ] && break
  sleep 2
done
if [ "$ISSUER" != "https://idp.lab:8443/realms/$REALM" ]; then
  echo "ÉCHEC : la porte TLS n'annonce pas l'issuer attendu." >&2
  echo "attendu https://idp.lab:8443/realms/$REALM, obtenu « $ISSUER »" >&2
  echo "Sans un issuer en https, le lab est injouable : l'apiserver refuse." >&2
  exit 1
fi

# ─── 3. Deux groupes, deux comptes ────────────────────────────────────────────
set +x
SECRET_DES_COMPTES=$(openssl rand -hex 12)
set -x

for groupe in "$GROUPE_DEVOPS" "$GROUPE_LECTEURS"; do
  admin POST "realms/$REALM/groups" \
    "$(jq -nc --arg n "$groupe" '{name:$n}')" > /dev/null
done

for duo in "$COMPTE_DEVOPS:$GROUPE_DEVOPS:Dalia:Kube" \
           "$COMPTE_LECTEUR:$GROUPE_LECTEURS:Lou:Lecture"; do
  compte=${duo%%:*}
  reste=${duo#*:}
  groupe=${reste%%:*}
  reste=${reste#*:}
  prenom=${reste%%:*}
  nom=${reste#*:}
  admin POST "realms/$REALM/users" "$(jq -nc --arg u "$compte" \
    --arg p "$prenom" --arg n "$nom" --arg e "$compte@formation.lab" '{
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

# ─── 4. L'outil de plateforme, debout et NON branché ──────────────────────────
# Il tourne avec son compte local d'administration, et ne connaît pas l'IdP.
# Le brancher est le travail. Le fichier d'environnement porte les clefs à
# remplir, et le script le redémarre : l'apprenant écrit des valeurs IAM, pas
# des arguments de docker.
cat > "$GRAFANA_ENV" <<CONF
# Branchement de l'outil sur le fournisseur d'identité, À COMPLÉTER.
#
# Remplissez les valeurs vides, puis jouez :
#     sudo $OUTILS/redemarrer-grafana.sh
#
# Le nom du fournisseur s'affiche sur la page de connexion de l'outil, ce qui
# est le moyen le plus simple de vérifier que ce fichier est bien lu.
GF_SERVER_ROOT_URL=http://$IP:3000/
GF_AUTH_GENERIC_OAUTH_ENABLED=
GF_AUTH_GENERIC_OAUTH_NAME=
GF_AUTH_GENERIC_OAUTH_CLIENT_ID=
GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET=
GF_AUTH_GENERIC_OAUTH_SCOPES=openid profile email
# Le client que vous déclarerez exigera PKCE. Cet outil n'en envoie pas de
# lui-même, et l'erreur part au CALLBACK : elle ressemble alors à un simple
# retour sur la page de connexion.
GF_AUTH_GENERIC_OAUTH_USE_PKCE=
GF_AUTH_GENERIC_OAUTH_AUTH_URL=
GF_AUTH_GENERIC_OAUTH_TOKEN_URL=
GF_AUTH_GENERIC_OAUTH_API_URL=
# Le certificat de l'IdP est auto-signé : l'outil doit le connaître pour
# joindre le point de jeton. Il est monté dans le conteneur à cet emplacement.
GF_AUTH_GENERIC_OAUTH_TLS_CLIENT_CA=/etc/ssl/certs/idp-lab.crt
# Le rôle dans l'outil, dérivé des groupes du jeton.
GF_AUTH_GENERIC_OAUTH_ROLE_ATTRIBUTE_PATH=
CONF
chown student:docker "$GRAFANA_ENV"
chmod 0660 "$GRAFANA_ENV"

cat > "$OUTILS/redemarrer-grafana.sh" <<CONF
#!/usr/bin/env bash
# Redémarre l'outil avec le contenu de $GRAFANA_ENV.
#
# Fourni pour que le travail porte sur les valeurs IAM et non sur les arguments
# de docker. Les lignes dont la valeur est vide sont écartées : une variable
# vide passée à l'outil vaut parfois « faux » et parfois « chaîne vide », et le
# diagnostic diffère.
set -euo pipefail
grep -vE '^\s*(#|\$)' "$GRAFANA_ENV" | grep -E '=.+' > /run/grafana-lab.env
docker rm -f grafana-lab > /dev/null 2>&1 || true
docker run -d --name grafana-lab \\
  --add-host "idp.lab:$IP" \\
  -p 3000:3000 \\
  --env-file /run/grafana-lab.env \\
  -v "$TLS/idp.crt:/etc/ssl/certs/idp-lab.crt:ro" \\
  "$IMAGE_GRAFANA" > /dev/null
rm -f /run/grafana-lab.env
echo "outil redémarré ; sa page de connexion est sur http://$IP:3000/login"
CONF
chmod 0755 "$OUTILS/redemarrer-grafana.sh"
bash "$OUTILS/redemarrer-grafana.sh" > /dev/null

# ─── 5. Ce que l'apprenant doit savoir pour commencer ─────────────────────────
set +x
{
  echo "# Posé par le setup du lab iam-14. Jetable."
  echo "REALM=${REALM}"
  echo "IP_MACHINE=${IP}"
  echo "COMPTES=${COMPTE_DEVOPS} ${COMPTE_LECTEUR}"
  printf 'MOT_DE_PASSE=%s\n' "$SECRET_DES_COMPTES"
  echo "GROUPE_DEVOPS=${GROUPE_DEVOPS}"
  echo "GROUPE_LECTEURS=${GROUPE_LECTEURS}"
  echo "COMPTE_DEVOPS=${COMPTE_DEVOPS}"
  echo "COMPTE_LECTEUR=${COMPTE_LECTEUR}"
  echo "CLUSTER_ATTENDU=${CLUSTER}"
  echo "NAMESPACE_ATTENDU=${NAMESPACE}"
  echo "CLIENT_KUBE_ATTENDU=kubernetes"
  echo "CLIENT_OUTIL_ATTENDU=grafana"
  echo "AUDIENCE_ATTENDUE=kubernetes"
  echo "ISSUER_TLS=https://idp.lab:8443/realms/${REALM}"
  echo "ISSUER_HTTP=${KC}/realms/${REALM}"
  echo "CA_IDP=${TLS}/idp.crt"
  echo "CONF_AUTH_ATTENDUE=${CONF_AUTH}/auth.yaml"
  echo "GRAFANA_ENV=${GRAFANA_ENV}"
  echo "GRAFANA_URL=http://${IP}:3000"
} > "$IDENTIFIANTS"
chown student:docker "$IDENTIFIANTS"
chmod 0640 "$IDENTIFIANTS"
set -x

# ─── 6. Contrôler l'état posé ─────────────────────────────────────────────────
# Sans ces contrôles, un lab parti d'un travail déjà fait serait vert avant
# d'avoir commencé.
CLUSTERS=$(k3d cluster list --no-headers 2>/dev/null | awk '{print $1}' | grep -c "^$CLUSTER$" || true)
CLIENT_KUBE=$(admin GET "realms/$REALM/clients?clientId=kubernetes" | jq 'length')

# L'outil met une quinzaine de secondes à servir sa page : il joue ses
# migrations de base avant d'écouter. Contrôler tout de suite après l'avoir
# démarré mesure le démarrage, pas l'outil.
CODE_OUTIL=000
for _ in $(seq 1 30); do
  CODE_OUTIL=$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' \
    "http://127.0.0.1:3000/login" 2>/dev/null || true)
  [ "$CODE_OUTIL" = "200" ] && break
  sleep 2
done
BOUTON=$(curl -sS --max-time 10 "http://127.0.0.1:3000/login" 2>/dev/null \
  | grep -c 'generic_oauth' || true)

if [ "$CLUSTERS" -ne 0 ] || [ "$CLIENT_KUBE" -ne 0 ] \
   || [ "$CODE_OUTIL" != "200" ] || [ "$BOUTON" -ne 0 ]; then
  echo "ÉCHEC : la situation de départ n'est pas celle attendue." >&2
  echo "clusters=$CLUSTERS client_kubernetes=$CLIENT_KUBE" >&2
  echo "outil_http=$CODE_OUTIL bouton_idp=$BOUTON (0 attendu partout" >&2
  echo "sauf outil_http=200)" >&2
  exit 1
fi

set +x
echo "Situation posée : k3d $K3D_VERSION et kubectl $KUBECTL_VERSION installés,"
echo "l'image du cluster tirée, un accès TLS devant l'IdP qui annonce"
echo "$ISSUER, deux groupes, deux comptes, et l'outil debout sur"
echo "http://$IP:3000 sans connaître l'IdP."
echo "Identifiants dans $IDENTIFIANTS"
