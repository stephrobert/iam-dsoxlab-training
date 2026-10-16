#!/usr/bin/env bash
# Pose la situation de l'ÉPREUVE DE NIVEAU 1, et la retire avec `--nettoyer`.
#
# UNE ÉPREUVE N'EST PAS UN LAB : elle ne pose aucune situation à corriger, elle
# retire tout ce qui pourrait tenir lieu de travail. Il n'y a donc PAS de
# fournisseur d'identité ici : l'installer est la première chose demandée.
#
# CE QU'ELLE FOURNIT, et seulement cela :
#   - la couche machine (Docker, Compose, les outils), posée par le setup ;
#   - les témoins, posés par le setup : une application et une API qui ne
#     savent rien du fournisseur ;
#   - un ANNUAIRE déjà peuplé, parce que le monter est le lab 01 et que cette
#     épreuve porte sur les labs 02 à 05 ;
#   - une API de départ qui répond SANS rien vérifier, à protéger ;
#   - le cahier des charges, dans le fichier d'identifiants.
#
# CE QU'ELLE RETIRE, et c'est le plus important : tout Keycloak, tout compose
# d'un passage précédent, et tout client. Une épreuve qui partirait du travail
# de la fois d'avant ne mesurerait rien.
#
# La trace va dans /var/log/dsoxlab-prepare.log, avec `set -x`, SUSPENDUE
# autour de chaque secret : ce journal est collecté par `dsoxlab support`.
set -euo pipefail

JOURNAL=/var/log/dsoxlab-prepare.log
exec > >(tee -a "$JOURNAL") 2>&1
set -x

EPREUVE=/opt/epreuve
ANNUAIRE=$EPREUVE/annuaire
LAB=/opt/iam-lab
API=$LAB/api-notes
IDENTIFIANTS=$LAB/identifiants-lab.txt
WEB=http://127.0.0.1:17170
PORT_LDAP=3890
PORT_API=8090
PORT_TEMOIN=9080

#: Le realm, les clients et les scopes que le cahier des charges impose. Les
#: tests lisent ces valeurs dans le fichier d'identifiants : aucune n'est
#: écrite deux fois.
REALM=formation
CLIENT_APPLI=appli-notes
CLIENT_API=notes-api
CLIENT_SERVICE=service-sauvegarde
CLIENT_DE_TEST=notes-cli
SCOPE_LECTURE="notes:lecture"
SCOPE_ECRITURE="notes:ecriture"
AUTRE_API=autre-api
SCOPE_AUTRE="autre:lecture"
ADMIN_NOMINATIF=admin-epreuve

IMAGE_LLDAP=${IMAGE_LLDAP:-}

IP=$(ip -4 -o addr show scope global \
     | awk 'NR == 1 { split($4, a, "/"); print a[1] }')
if [ -z "$IP" ]; then
  echo "ÉCHEC : aucune adresse IPv4 globale sur cette machine." >&2
  exit 1
fi

arreter_l_annuaire() {
  if [ -f "$ANNUAIRE/compose.yaml" ]; then
    (cd "$ANNUAIRE" && docker compose -f compose.yaml --env-file .env \
      down --volumes --remove-orphans > /dev/null 2>&1) || true
  fi
  docker rm -f epreuve-annuaire-lldap-1 > /dev/null 2>&1 || true
  docker volume rm epreuve-annuaire_lldapdata > /dev/null 2>&1 || true
  return 0
}

retirer_le_socle_d_un_autre_lab() {
  # LA MACHINE EST PARTAGÉE ENTRE LES LABS, et le socle IAM qu'un autre lab a
  # posé occupe 8080, 9000, 3890 et 17170 : exactement les ports de cette
  # épreuve. Il part, VOLUMES COMPRIS, comme le fait le lab 02 pour la même
  # raison : une base qui survivrait ferait retrouver un realm déjà peuplé.
  if [ -f /opt/socle-iam/compose.yaml ]; then
    (cd /opt/socle-iam && docker compose --env-file .env down -v \
      --remove-orphans > /dev/null 2>&1) || true
  fi
  return 0
}

retirer_le_travail() {
  # TOUT ce que la candidate a pu monter. Un Keycloak qui survivrait rendrait
  # la première question gratuite.
  local conteneur reseau
  for repertoire in /opt/keycloak-lab "$EPREUVE/keycloak"; do
    if [ -f "$repertoire/compose.yaml" ]; then
      (cd "$repertoire" && docker compose -f compose.yaml down --volumes \
        --remove-orphans > /dev/null 2>&1) || true
    fi
  done
  # Par le nom aussi : un compose supprimé laisse des conteneurs que
  # `docker compose down` ne sait plus désigner.
  for conteneur in $(docker ps -aq --filter 'name=keycloak' 2>/dev/null); do
    docker rm -f "$conteneur" > /dev/null 2>&1 || true
  done
  for conteneur in $(docker ps -aq --filter 'name=epreuve' 2>/dev/null); do
    # L'annuaire de l'épreuve est retiré séparément, pour qu'un nettoyage
    # partiel ne le laisse pas orphelin.
    docker rm -f "$conteneur" > /dev/null 2>&1 || true
  done
  for reseau in $(docker network ls -q --filter 'name=keycloak' 2>/dev/null); do
    docker network rm "$reseau" > /dev/null 2>&1 || true
  done
  for volume in $(docker volume ls -q --filter 'name=keycloak' 2>/dev/null); do
    docker volume rm "$volume" > /dev/null 2>&1 || true
  done
  # Les témoins que la candidate aurait démarrés.
  for port in "$PORT_TEMOIN" "$PORT_API"; do
    [ -x "$LAB/outils/arreter-temoin.sh" ] \
      && "$LAB/outils/arreter-temoin.sh" "$port" > /dev/null 2>&1 || true
  done
  rm -f "$LAB/appli-temoin/configuration.json"
  return 0
}

# ─── Mode nettoyage, appelé par cleanup.yaml ──────────────────────────────────
if [ "${1:-}" = "--nettoyer" ]; then
  retirer_le_travail
  retirer_le_socle_d_un_autre_lab
  arreter_l_annuaire
  rm -f "$ANNUAIRE/compose.yaml" "$ANNUAIRE/.env" "$IDENTIFIANTS"
  rm -f "$API/api.py" "$API/api.log"
  rmdir "$ANNUAIRE" "$EPREUVE" 2>/dev/null || true
  echo "nettoyage de l'épreuve de niveau 1 terminé"
  exit 0
fi

# ─── À partir d'ici, la version de l'annuaire est indispensable ───────────────
if [ -z "$IMAGE_LLDAP" ]; then
  echo "ÉCHEC : IMAGE_LLDAP n'est pas fournie. Le setup la lit dans" >&2
  echo "shared/images.yml et la passe en variable d'environnement." >&2
  exit 1
fi

retirer_le_socle_d_un_autre_lab
retirer_le_travail
arreter_l_annuaire

# ─── 1. L'annuaire, seul, et déjà peuplé ──────────────────────────────────────
mkdir -p "$ANNUAIRE" "$API"
set +x
umask 077
BASE_DN="dc=formation,dc=lab"
MDP_LDAP=$(openssl rand -hex 16)
{
  printf 'IMAGE_LLDAP=%s\n' "$IMAGE_LLDAP"
  printf 'LLDAP_JWT_SECRET=%s\n' "$(openssl rand -hex 24)"
  printf 'LLDAP_KEY_SEED=%s\n' "$(openssl rand -hex 24)"
  printf 'LLDAP_BASE_DN=%s\n' "$BASE_DN"
  printf 'LLDAP_ADMIN_PASSWORD=%s\n' "$MDP_LDAP"
} > "$ANNUAIRE/.env"
chown student:docker "$ANNUAIRE/.env"
chmod 0640 "$ANNUAIRE/.env"
set -x

cat > "$ANNUAIRE/compose.yaml" <<'CONF'
# L'annuaire de l'épreuve de niveau 1.
#
# SEUL : il n'y a pas de fournisseur d'identité ici, l'installer est la
# première question de l'épreuve. L'annuaire est fourni parce que le monter est
# le sujet du lab 01, hors du périmètre de cette épreuve.
#
# Son port LDAP est PUBLIÉ sur la machine : le fournisseur que la candidate
# montera vivra dans un autre réseau Docker, et ne résoudra donc pas « lldap ».
# C'est l'adresse de la MACHINE qu'il devra viser, et sûrement pas 127.0.0.1,
# qui depuis un conteneur désigne le conteneur lui-même.
name: epreuve-annuaire

services:
  lldap:
    image: ${IMAGE_LLDAP}
    environment:
      LLDAP_JWT_SECRET: ${LLDAP_JWT_SECRET}
      LLDAP_KEY_SEED: ${LLDAP_KEY_SEED}
      LLDAP_LDAP_BASE_DN: ${LLDAP_BASE_DN}
      LLDAP_LDAP_USER_PASS: ${LLDAP_ADMIN_PASSWORD}
      LLDAP_DATABASE_URL: "sqlite:///data/users.db?mode=rwc"
    volumes:
      - lldapdata:/data
    ports:
      - "3890:3890"
      - "17170:17170"
    restart: unless-stopped

volumes:
  lldapdata:
CONF
chown student:docker "$ANNUAIRE/compose.yaml"
chmod 0640 "$ANNUAIRE/compose.yaml"

# La sortie n'est PAS masquée : un port déjà pris s'y voit, et la masquer m'a
# fait chercher la cause ailleurs pendant un moment.
(cd "$ANNUAIRE" && docker compose -f compose.yaml --env-file .env up -d)

# Attendre l'annuaire, et le DIRE s'il ne vient pas.
PRET=
for _ in $(seq 1 45); do
  CODE=$(curl -sS --max-time 4 -o /dev/null -w '%{http_code}' \
    "$WEB/" 2>/dev/null || true)
  if [ "$CODE" = "200" ]; then PRET=oui; break; fi
  sleep 2
done
if [ -z "$PRET" ]; then
  echo "ÉCHEC : l'annuaire ne répond pas sur $WEB." >&2
  docker logs epreuve-annuaire-lldap-1 2>&1 | tail -15 >&2
  exit 1
fi

set +x
JETON_LDAP=$(curl -sS --max-time 20 -X POST "$WEB/auth/simple/login" \
  -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg m "$MDP_LDAP" '{username:"admin", password:$m}')" \
  | jq -r '.token // empty')
if [ -z "$JETON_LDAP" ]; then
  echo "ÉCHEC : aucun jeton de l'API de l'annuaire." >&2
  exit 1
fi
set -x

lldap_api() {
  set +x
  curl -sS --max-time 20 -X POST "$WEB/api/graphql" \
    -H "Authorization: Bearer $JETON_LDAP" -H 'Content-Type: application/json' \
    -d "$1"
  set -x
}

set +x
SECRET_DES_COMPTES=$(openssl rand -hex 12)
LDAP="ldap://127.0.0.1:$PORT_LDAP"
ADMIN_DN="uid=admin,ou=people,$BASE_DN"
set -x

cat > /tmp/personnes-epreuve.ldif <<LDIF
dn: uid=aline,ou=people,$BASE_DN
objectClass: inetOrgPerson
uid: aline
cn: Aline Dupont
sn: Dupont
mail: aline@formation.lab

dn: uid=bruno,ou=people,$BASE_DN
objectClass: inetOrgPerson
uid: bruno
cn: Bruno Keller
sn: Keller
mail: bruno@formation.lab

dn: uid=chloe,ou=people,$BASE_DN
objectClass: inetOrgPerson
uid: chloe
cn: Chloe Nguyen
sn: Nguyen
mail: chloe@formation.lab
LDIF

set +x
ldapadd -x -H "$LDAP" -D "$ADMIN_DN" -w "$MDP_LDAP" \
  -f /tmp/personnes-epreuve.ldif
for compte in aline bruno chloe; do
  ldappasswd -x -H "$LDAP" -D "$ADMIN_DN" -w "$MDP_LDAP" \
    -s "$SECRET_DES_COMPTES" "uid=$compte,ou=people,$BASE_DN"
done
set -x
rm -f /tmp/personnes-epreuve.ldif

cat > /tmp/groupes-epreuve.ldif <<LDIF
dn: cn=devops,ou=groups,$BASE_DN
objectClass: groupOfNames
cn: devops

dn: cn=lecteurs,ou=groups,$BASE_DN
objectClass: groupOfNames
cn: lecteurs
LDIF
set +x
ldapadd -x -H "$LDAP" -D "$ADMIN_DN" -w "$MDP_LDAP" -f /tmp/groupes-epreuve.ldif
set -x
rm -f /tmp/groupes-epreuve.ldif

# Les appartenances passent par l'API : un `member:` dans un LDIF de groupe est
# accepté puis IGNORÉ par LLDAP. C'est ce que le lab 01 fait découvrir.
IDS_GROUPES=$(lldap_api '{"query":"{ groups { id displayName } }"}')
for duo in "devops:aline bruno" "lecteurs:chloe"; do
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

# ─── 2. L'API de départ : elle répond, et ne vérifie RIEN ─────────────────────
# C'est le point de départ du travail : une API ouverte, qu'il faut fermer.
cat > "$API/api.py" <<'PY'
"""API témoin « notes » : version de DÉPART, qui ne vérifie rien.

Elle répond 200 à qui demande, avec ou sans jeton. C'est exactement le défaut
à corriger : une API qui sert des données sans savoir à qui.

Le travail consiste à lui faire vérifier la signature, l'issuer, l'audience et
l'expiration du jeton, puis le scope selon la méthode. Le refus
d'authentification est un 401 ; le refus d'autorisation un 403.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(os.environ.get("PORT_API", "8090"))

NOTES = [
    {"id": 1, "titre": "Reunion de lancement", "contenu": "Jeudi 14h"},
    {"id": 2, "titre": "Astreinte", "contenu": "Semaine 42 : Aline"},
]


class Gestionnaire(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def repondre(self, code: int, charge: object) -> None:
        corps = json.dumps(charge).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") == "/notes":
            self.repondre(200, {"notes": NOTES})
        else:
            self.repondre(404, {"erreur": "chemin inconnu"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") == "/notes":
            self.repondre(201, {"cree": True})
        else:
            self.repondre(404, {"erreur": "chemin inconnu"})

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", PORT), Gestionnaire).serve_forever()
PY
chown student:docker "$API/api.py"
chmod 0660 "$API/api.py"

"$LAB/outils/arreter-temoin.sh" "$PORT_API" > /dev/null 2>&1 || true
install -o student -g docker -m 0660 /dev/null "$API/api.log"
sudo -u student env PORT_API="$PORT_API" \
  setsid nohup "$LAB/appli-temoin/.venv/bin/python" "$API/api.py" \
  > "$API/api.log" 2>&1 &
sleep 1

PRET_API=
for _ in $(seq 1 20); do
  if curl -sS -o /dev/null --max-time 2 "http://127.0.0.1:$PORT_API/notes"; then
    PRET_API=oui
    break
  fi
  sleep 1
done
if [ -z "$PRET_API" ]; then
  echo "ÉCHEC : l'API de départ ne répond pas sur le port $PORT_API." >&2
  tail -15 "$API/api.log" >&2
  exit 1
fi

# ─── 3. Le cahier des charges ─────────────────────────────────────────────────
set +x
{
  echo "# ÉPREUVE DE NIVEAU 1. Posé par le setup. Jetable."
  echo "# Ce fichier EST le cahier des charges : les tests lisent ces valeurs."
  echo "DEBUT_EPREUVE=$(date -Iseconds)"
  echo "DUREE_VISEE_MINUTES=90"
  echo "IP_MACHINE=${IP}"
  echo "REALM_ATTENDU=${REALM}"
  echo "ADMIN_NOMINATIF_ATTENDU=${ADMIN_NOMINATIF}"
  printf 'ADMIN_MOT_DE_PASSE=%s\n' "$(openssl rand -hex 12)"
  echo "URL_KEYCLOAK_ATTENDUE=http://127.0.0.1:8080"
  echo "PORT_GESTION_ATTENDU=9000"
  echo "# L'annuaire, déjà peuplé. Son port LDAP est publié SUR LA MACHINE."
  echo "LDAP_BASE_DN=${BASE_DN}"
  echo "LDAP_USERS_DN=ou=people,${BASE_DN}"
  echo "LDAP_GROUPS_DN=ou=groups,${BASE_DN}"
  echo "LDAP_ADMIN_DN=${ADMIN_DN}"
  printf 'LDAP_ADMIN_MOT_DE_PASSE=%s\n' "$MDP_LDAP"
  echo "LDAP_PORT=${PORT_LDAP}"
  echo "LDAP_COMPTES=aline bruno chloe"
  echo "LDAP_GROUPE_DEVOPS=devops"
  echo "LDAP_GROUPE_LECTEURS=lecteurs"
  printf 'MOT_DE_PASSE=%s\n' "$SECRET_DES_COMPTES"
  echo "UTILISATEUR=aline"
  echo "# Les clients et les scopes attendus."
  echo "CLIENT_APPLI_ATTENDU=${CLIENT_APPLI}"
  echo "CLIENT_API_ATTENDU=${CLIENT_API}"
  echo "CLIENT_SERVICE_ATTENDU=${CLIENT_SERVICE}"
  echo "CLIENT_DE_TEST_ATTENDU=${CLIENT_DE_TEST}"
  echo "SCOPE_LECTURE=${SCOPE_LECTURE}"
  echo "SCOPE_ECRITURE=${SCOPE_ECRITURE}"
  echo "AUTRE_API=${AUTRE_API}"
  echo "SCOPE_AUTRE_API=${SCOPE_AUTRE}"
  echo "# Les témoins, à brancher."
  echo "PORT_APPLI_TEMOIN=${PORT_TEMOIN}"
  echo "PORT_API=${PORT_API}"
  echo "REPERTOIRE_APPLI=${LAB}/appli-temoin"
  echo "REPERTOIRE_API=${API}"
} > "$IDENTIFIANTS"
chown student:docker "$IDENTIFIANTS"
chmod 0640 "$IDENTIFIANTS"
set -x

# ─── 4. Contrôler l'état posé ─────────────────────────────────────────────────
# Une épreuve doit partir de RIEN côté fournisseur. Sans ces contrôles, une
# candidate pourrait être notée sur le travail du passage précédent.
CODE_KC=$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' \
  "http://127.0.0.1:8080/realms/master" 2>/dev/null || true)
CODE_ANNUAIRE=$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' \
  "$WEB/" 2>/dev/null || true)
CODE_API=$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' \
  "http://127.0.0.1:$PORT_API/notes" 2>/dev/null || true)
COMPTES_LDAP=$(ldapsearch -x -H "$LDAP" -D "$ADMIN_DN" -w "$MDP_LDAP" \
  -b "ou=people,$BASE_DN" -s one '(objectClass=inetOrgPerson)' uid 2>/dev/null \
  | grep -c '^uid:' || true)

if [ "$CODE_KC" = "200" ] || [ "$CODE_ANNUAIRE" != "200" ] \
   || [ "$CODE_API" != "200" ] || [ "$COMPTES_LDAP" -lt 4 ]; then
  echo "ÉCHEC : la situation de départ n'est pas celle attendue." >&2
  echo "keycloak=$CODE_KC (doit être muet) annuaire=$CODE_ANNUAIRE (200)" >&2
  echo "api_de_depart=$CODE_API (200) comptes_ldap=$COMPTES_LDAP (admin + 3)" >&2
  exit 1
fi

set +x
echo "Épreuve de niveau 1 : aucun fournisseur d'identité, un annuaire peuplé"
echo "de 3 comptes et 2 groupes sur l'adresse $IP, une API de départ ouverte"
echo "sur le port $PORT_API, et les témoins prêts à être branchés."
echo "Le cahier des charges est dans $IDENTIFIANTS"
