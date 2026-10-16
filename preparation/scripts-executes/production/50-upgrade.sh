#!/usr/bin/env bash
set -u
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-production/lib.sh
psqlq() { docker compose exec -T db psql -U keycloak -d keycloak -At -c "$1"; }
OLD=quay.io/keycloak/keycloak:26.7.0@sha256:0f198be292568439d700cdbfb893e69a6009bb43a94a06a945b1d3d506c76b13
NEW=quay.io/keycloak/keycloak:26.8.1@sha256:79c623a22abacf3fe6c00a5fb30f5b7843d717b234033b80995891c06116d244
echo "##### 5a. Avant : serveur arrete, sauvegarde fraiche, etat de reference"
docker compose stop keycloak proxy 2>&1 | tail -1
docker compose exec -T db pg_dump -U keycloak -d keycloak --format=custom --no-owner > $L/backup/avant-26.8.1.dump
ls -l $L/backup/avant-26.8.1.dump | awk '{print $5, $9}' | sed "s#$L/##"
echo "version du schema (migration_model) : $(psqlq 'select version from migration_model')"
echo "utilisateurs=$(psqlq "select count(*) from user_entity") clients=$(psqlq "select count(*) from client") realms=$(psqlq "select string_agg(name, ',' order by name) from realm")"

echo
echo "##### 5b. Changement d'image (tag ET digest) dans compose.yaml"
cp compose.yaml compose.avant.yaml
sed -i "s#image: $OLD#image: $NEW#" compose.yaml
diff compose.avant.yaml compose.yaml | sed 's/^/  /'
docker pull "$NEW" | tail -2
docker compose up -d 2>&1 | tail -4
SECONDS=0
attendre
echo "duree de la montee jusqu'a /health/ready : ${SECONDS}s"
echo "-- journal de la migration"
docker compose logs keycloak 2>&1 | grep -i -E "Updating the database|Database update|migrat|liquibase|Keycloak 26.* started|KC-SERVICES0077" | cut -c1-260 | head -12

echo
echo "##### 5c. Apres : memes verifications"
echo "version du schema (migration_model) : $(psqlq 'select version from migration_model')"
echo "utilisateurs=$(psqlq "select count(*) from user_entity") clients=$(psqlq "select count(*) from client") realms=$(psqlq "select string_agg(name, ',' order by name) from realm")"
cpub $PUB/realms/formation/.well-known/openid-configuration | jq -r '.issuer'
cpub -X POST $PUB/realms/formation/protocol/openid-connect/token -d grant_type=password -d client_id=appli -d username=alice -d password='Alice-lab-2026' | jq -c '{token_type, expires_in, connexion_ok: (.access_token != null)}'
echo "-- le refresh token pris AVANT la montee fonctionne-t-il ?"
cpub -X POST $PUB/realms/formation/protocol/openid-connect/token -d grant_type=refresh_token -d client_id=appli -d refresh_token="$(cat $D/refresh-alice.txt)" | jq -c '{refresh_ok: (.access_token != null), error}'
echo "-- version annoncee par le serveur"
docker compose exec -T keycloak sh -c '/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user temp-admin --password "$KC_BOOTSTRAP_ADMIN_PASSWORD"' >/dev/null
kcadm get serverinfo --fields systemInfo | jq -c '.systemInfo | {version}'
echo "-- admin console : refus public conserve ?"
cpub -o /dev/null -w 'public /admin/master/console/: %{http_code}\n' $PUB/admin/master/console/
cadm -o /dev/null -w 'admin /admin/master/console/: %{http_code}\n' $ADM/admin/master/console/
