#!/usr/bin/env bash
set -u
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-production/lib.sh
psqlq() { docker compose exec -T db psql -U keycloak -d "${DB:-keycloak}" -At -c "$1"; }
echo "##### Donnees du realm avant sauvegarde : evenements, session, utilisateurs"
docker compose exec -T keycloak sh -c '/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user temp-admin --password "$KC_BOOTSTRAP_ADMIN_PASSWORD"' >/dev/null
kcadm update events/config -r formation -s eventsEnabled=true -s adminEventsEnabled=true -s 'enabledEventTypes=["LOGIN","LOGIN_ERROR"]'
kcadm create users -r formation -s username=bob -s enabled=true -s email=bob@exemple.fr
kcadm set-password -r formation --username bob --new-password 'Bob-lab-2026'
# une session ouverte, un echec de connexion
cpub -X POST $PUB/realms/formation/protocol/openid-connect/token -d grant_type=password -d client_id=appli -d username=alice -d password='Alice-lab-2026' -d scope=openid | jq -r '.refresh_token' > $D/refresh-alice.txt
cpub -o /dev/null -w 'echec volontaire: HTTP %{http_code}\n' -X POST $PUB/realms/formation/protocol/openid-connect/token -d grant_type=password -d client_id=appli -d username=alice -d password='faux'
echo "-- tables de session presentes dans la base :"
psqlq "select tablename from pg_tables where schemaname='public' and tablename like '%session%' order by 1"
echo "-- lignes : user_session / offline_user_session / event_entity / admin_event_entity / user_entity"
for t in user_session offline_user_session event_entity admin_event_entity user_entity; do printf '%s=' $t; psqlq "select count(*) from $t"; done
echo "-- realms et clients du realm formation"
psqlq "select name from realm order by 1"
kcadm get clients -r formation --fields clientId --format csv --noquotes | sort | tr '\n' ' '; echo

echo
echo "##### 4a. pg_dump au format custom"
mkdir -p $L/backup && chmod 700 $L/backup
STAMP=26.7.0
docker compose exec -T db pg_dump -U keycloak -d keycloak --format=custom --no-owner > $L/backup/keycloak-$STAMP.dump
ls -l $L/backup/keycloak-$STAMP.dump | awk '{print $5, $9}'
sha256sum $L/backup/keycloak-$STAMP.dump | cut -c1-16
echo "-- contenu lisible par pg_restore --list (les 4 premieres tables de donnees)"
docker compose exec -T db pg_restore --list < $L/backup/keycloak-$STAMP.dump | grep -E "TABLE DATA public (realm|user_entity|client|user_session) " | head -6

echo
echo "##### 4b. Restauration dans une base VIDE"
docker compose exec -T db createdb -U keycloak keycloak_restore
DB=keycloak_restore psqlq "select count(*) from information_schema.tables where table_schema='public'" | sed 's/^/tables avant restauration: /'
docker compose exec -T db pg_restore -U keycloak -d keycloak_restore --no-owner < $L/backup/keycloak-$STAMP.dump; echo "pg_restore code retour: $?"
for t in user_entity user_session event_entity admin_event_entity; do printf '%s (restauree)=' $t; DB=keycloak_restore psqlq "select count(*) from $t"; done
DB=keycloak_restore psqlq "select name from realm order by 1" | tr '\n' ' '; echo

echo
echo "##### 4c. Un Keycloak 26.7.0 demarre sur la base restauree"
docker compose run -d --no-deps --name prod-kc-restore -e KC_DB_URL=jdbc:postgresql://db:5432/keycloak_restore keycloak start >/dev/null
for i in $(seq 1 60); do
  docker run --rm --network container:prod-kc-restore curlimages/curl:8.23.0@sha256:a134550be58ab783810e613ae96fd253c38f7bdd16d9bf9be350700c7a29ac06 -s -f -o /dev/null http://localhost:9000/health/ready && break; sleep 2
done
echo "pret apres ${i}x2s"
docker run --rm --network container:prod-kc-restore curlimages/curl:8.23.0@sha256:a134550be58ab783810e613ae96fd253c38f7bdd16d9bf9be350700c7a29ac06 -s -X POST http://localhost:8080/realms/formation/protocol/openid-connect/token -d grant_type=password -d client_id=appli -d username=alice -d password='Alice-lab-2026' | jq -c '{token_type, expires_in, ok: (.access_token != null)}'
docker run --rm --network container:prod-kc-restore curlimages/curl:8.23.0@sha256:a134550be58ab783810e613ae96fd253c38f7bdd16d9bf9be350700c7a29ac06 -s -X POST http://localhost:8080/realms/formation/protocol/openid-connect/token -d grant_type=refresh_token -d client_id=appli -d refresh_token="$(cat $D/refresh-alice.txt)" | jq -c '{refresh_ok: (.access_token != null), error}'
docker rm -f prod-kc-restore >/dev/null
docker compose exec -T db dropdb -U keycloak keycloak_restore && echo "base de restauration supprimee"
