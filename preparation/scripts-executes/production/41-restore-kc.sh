#!/usr/bin/env bash
set -u
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-production/lib.sh
CURL=curlimages/curl:8.23.0@sha256:a134550be58ab783810e613ae96fd253c38f7bdd16d9bf9be350700c7a29ac06
psqlq() { docker compose exec -T db psql -U keycloak -d "${DB:-keycloak}" -At -c "$1"; }
echo "-- sessions dans la base (offline_flag : true = hors ligne, false = session classique)"
psqlq "select offline_flag, count(*) from offline_user_session group by 1 order by 1"
docker compose exec -T db createdb -U keycloak keycloak_restore
docker compose exec -T db pg_restore -U keycloak -d keycloak_restore --no-owner < $L/backup/keycloak-26.7.0.dump; echo "pg_restore: $?"
docker compose run -d --no-deps --name prod-kc-restore -e KC_DB_URL=jdbc:postgresql://db:5432/keycloak_restore keycloak start >/dev/null
for i in $(seq 1 90); do
  docker run --rm --network container:prod-kc-restore $CURL -s -f -o /dev/null http://localhost:9000/health/ready && break
  [ "$(docker inspect -f '{{.State.Running}}' prod-kc-restore)" = true ] || { echo "conteneur arrete"; break; }
  sleep 2
done
echo "tentatives: $i"
docker logs prod-kc-restore 2>&1 | grep -E "started in|ERROR|Caused|FATAL" | cut -c1-300 | head -8
docker run --rm --network container:prod-kc-restore $CURL -s -X POST http://localhost:8080/realms/formation/protocol/openid-connect/token -d grant_type=password -d client_id=appli -d username=alice -d password='Alice-lab-2026' | jq -c '{token_type, expires_in, ok: (.access_token != null)}'
docker run --rm --network container:prod-kc-restore $CURL -s -X POST http://localhost:8080/realms/formation/protocol/openid-connect/token -d grant_type=refresh_token -d client_id=appli -d refresh_token="$(cat $D/refresh-alice.txt)" | jq -c '{refresh_ok: (.access_token != null), error}'
docker rm -f prod-kc-restore >/dev/null
docker compose exec -T db dropdb -U keycloak keycloak_restore && echo "base de restauration supprimee"
