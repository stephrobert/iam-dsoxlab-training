#!/usr/bin/env bash
set -u
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-production/lib.sh
psqlq() { docker compose exec -T db psql -U keycloak -d keycloak -At -c "$1"; }
KCI=quay.io/keycloak/keycloak:26.8.1@sha256:79c623a22abacf3fe6c00a5fb30f5b7843d717b234033b80995891c06116d244
echo "-- version du schema apres la montee (derniere ligne de migration_model)"
psqlq "select version from migration_model order by update_time desc limit 1"
echo "-- version annoncee par le serveur"
docker compose exec -T keycloak sh -c '/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user temp-admin --password "$KC_BOOTSTRAP_ADMIN_PASSWORD"' >/dev/null
kcadm get serverinfo | jq -c '.systemInfo.version'

echo
echo "##### 6a. Compte administrateur perdu (simulation : le seul admin est supprime)"
TID=$(kcadm get users -r master -q username=temp-admin --fields id --format csv --noquotes)
kcadm delete users/$TID -r master && echo "temp-admin supprime"
cadm -o /dev/null -w 'connexion temp-admin apres suppression: HTTP %{http_code}\n' -X POST $ADM/realms/master/protocol/openid-connect/token -d grant_type=password -d client_id=admin-cli -d username=temp-admin --data-urlencode "password=$(grep KC_ADMIN_PASSWORD .env | cut -d= -f2)"

echo "-- recuperation : arret du serveur, puis bootstrap-admin dans un conteneur jetable, memes options de base"
docker compose stop keycloak proxy 2>&1 | tail -1
SECOURS_PW=$(openssl rand -hex 16)
docker compose run --rm --no-deps -e SECOURS_PW="$SECOURS_PW" keycloak bootstrap-admin user --username secours --password:env SECOURS_PW --no-prompt 2>&1 | grep -v -E "^$|Deprecated" | cut -c1-250
docker compose up -d 2>&1 | tail -2
attendre
cadm -X POST $ADM/realms/master/protocol/openid-connect/token -d grant_type=password -d client_id=admin-cli -d username=secours --data-urlencode "password=$SECOURS_PW" -o $D/secours.json -w 'connexion secours: HTTP %{http_code}\n'
ATOK=$(jq -r .access_token $D/secours.json)
cadm -H "Authorization: Bearer $ATOK" $ADM/admin/realms | jq -c '[.[].realm]'
echo "-- le compte est temporaire : la console le signale, et il faut le remplacer"
docker compose logs keycloak 2>&1 | grep -E "temporary|temporaire" | cut -c1-250 | tail -3
echo "-- remplacement par un compte permanent nominatif, puis suppression du compte de secours"
docker compose exec -T -e SECOURS_PW="$SECOURS_PW" keycloak sh -c '/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user secours --password "$SECOURS_PW"' >/dev/null
kcadm create users -r master -s username=admin-sr -s enabled=true
kcadm set-password -r master --username admin-sr --new-password "$(openssl rand -hex 16)"
kcadm add-roles -r master --uusername admin-sr --rolename admin
SID=$(kcadm get users -r master -q username=secours --fields id --format csv --noquotes)
kcadm delete users/$SID -r master && echo "compte de secours supprime"
kcadm get users -r master --fields username --format csv --noquotes | sort | tr '\n' ' '; echo

echo
echo "##### 7. Panne de l'IdP"
cpub -X POST $PUB/realms/formation/protocol/openid-connect/token -d grant_type=password -d client_id=appli -d username=alice -d password='Alice-lab-2026' -d scope=openid > $D/tok.json
jq -r .access_token $D/tok.json > $D/at.txt
jq -r .refresh_token $D/tok.json > $D/rt.txt
cpub $PUB/realms/formation/protocol/openid-connect/certs > $D/jwks.json
cut -d. -f2 $D/at.txt | tr '_-' '/+' | { read -r s; while [ $(( ${#s} % 4 )) -ne 0 ]; do s="$s="; done; echo "$s" | base64 -d; } | jq -c '{iat, exp, duree: (.exp - .iat)}'
echo "-- Keycloak en marche"
$D/venv/bin/python $D/verif.py $D/at.txt $D/jwks.json $PUB/realms/formation
echo "-- docker compose stop keycloak"
docker compose stop keycloak 2>&1 | tail -1
echo "-- jeton deja emis, verifie avec la copie locale du JWKS"
$D/venv/bin/python $D/verif.py $D/at.txt $D/jwks.json $PUB/realms/formation
echo "-- application qui recupere le JWKS a chaque verification"
cpub -o /dev/null -w 'GET .../certs : HTTP %{http_code}\n' $PUB/realms/formation/protocol/openid-connect/certs
echo "-- nouvelle connexion"
cpub -o /dev/null -w 'POST .../token (password) : HTTP %{http_code}\n' -X POST $PUB/realms/formation/protocol/openid-connect/token -d grant_type=password -d client_id=appli -d username=alice -d password='Alice-lab-2026'
echo "-- renouvellement par refresh token"
cpub -o /dev/null -w 'POST .../token (refresh) : HTTP %{http_code}\n' -X POST $PUB/realms/formation/protocol/openid-connect/token -d grant_type=refresh_token -d client_id=appli -d refresh_token="$(cat $D/rt.txt)"
echo "-- redemarrage"
docker compose start keycloak 2>&1 | tail -1
attendre
cpub -X POST $PUB/realms/formation/protocol/openid-connect/token -d grant_type=refresh_token -d client_id=appli -d refresh_token="$(cat $D/rt.txt)" | jq -c '{refresh_ok: (.access_token != null), error}'
