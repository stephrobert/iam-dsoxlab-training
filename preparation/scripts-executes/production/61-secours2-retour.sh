#!/usr/bin/env bash
set -u
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-production/lib.sh
CURL=curlimages/curl:8.23.0@sha256:a134550be58ab783810e613ae96fd253c38f7bdd16d9bf9be350700c7a29ac06
echo "##### Verification du compte permanent admin-sr (mot de passe inconnu : on repasse par le compte de secours)"
cadm -w ' HTTP %{http_code}\n' -X POST $ADM/realms/master/protocol/openid-connect/token -d grant_type=password -d client_id=admin-cli -d username=temp-admin -d password=nimporte | cut -c1-200
docker compose stop keycloak proxy 2>&1 | tail -1
SECOURS_PW=$(openssl rand -hex 16)
docker compose run --rm --no-deps -e SECOURS_PW="$SECOURS_PW" keycloak bootstrap-admin user --username secours --password:env SECOURS_PW --no-prompt 2>&1 | grep -E "KC-SERVICES0077|ERROR"
docker compose up -d 2>&1 | tail -1
attendre
docker compose exec -T -e SECOURS_PW="$SECOURS_PW" keycloak sh -c '/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user secours --password "$SECOURS_PW"' >/dev/null
PERM_PW=$(openssl rand -hex 16)
kcadm set-password -r master --username admin-sr --new-password "$PERM_PW"
docker compose exec -T -e PERM_PW="$PERM_PW" keycloak sh -c '/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin-sr --password "$PERM_PW"' >/dev/null && echo "connexion admin-sr: ok"
SID=$(kcadm get users -r master -q username=secours --fields id --format csv --noquotes)
kcadm delete users/$SID -r master && echo "compte de secours supprime"
kcadm get users -r master --fields username --format csv --noquotes | sort | tr '\n' ' '; echo
kcadm get realms --fields realm --format csv --noquotes | sort | tr '\n' ' '; echo

echo
echo "##### Retour arriere : 26.7.0 sur une base deja migree en 26.8 (copie)"
docker compose exec -T db createdb -U keycloak keycloak_down
docker compose exec -T db pg_dump -U keycloak -d keycloak --format=custom --no-owner | docker compose exec -T db pg_restore -U keycloak -d keycloak_down --no-owner
OLD=quay.io/keycloak/keycloak:26.7.0@sha256:0f198be292568439d700cdbfb893e69a6009bb43a94a06a945b1d3d506c76b13
# l'image 26.7.0 est lancee directement, avec les memes variables
ENVF=$(mktemp); docker compose config --format json | jq -r '.services.keycloak.environment | to_entries[] | "\(.key)=\(.value)"' > $ENVF
docker run -d --name prod-kc-down --network prod_default --env-file $ENVF -e KC_DB_URL=jdbc:postgresql://db:5432/keycloak_down $OLD start >/dev/null
rm -f $ENVF
sleep 25
docker logs prod-kc-down 2>&1 | grep -E "started in|ERROR|Caused by|Unable|FATAL|migrat|Updating|newer|version" | cut -c1-300 | head -10
docker rm -f prod-kc-down >/dev/null
docker compose exec -T db dropdb -U keycloak keycloak_down && echo "base de test supprimee"
