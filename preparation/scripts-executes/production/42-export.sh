#!/usr/bin/env bash
set -u
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-production/lib.sh
echo "##### Export du realm formation (serveur arrete)"
docker compose stop keycloak proxy 2>&1 | tail -2
mkdir -p $L/export && chmod 777 $L/export
docker compose run --rm --no-deps -v $L/export:/export keycloak export --dir /export --realm formation 2>&1 | grep -E "Export finished|Realm '|ERROR|Exporting" | cut -c1-250
ls -l $L/export | awk 'NR>1{print $5, $9}'
cd $L/export
echo "-- cles de premier niveau du fichier de realm (extrait)"
jq -r 'keys | join(" ")' formation-realm.json | fold -w 200
echo "-- evenements ou sessions dans l'export ?"
grep -l -E '"eventsEnabled"' formation-realm.json >/dev/null && echo "reglage eventsEnabled present: $(jq .eventsEnabled formation-realm.json)"
jq -r 'has("events") , has("adminEvents"), has("userSessions"), has("offlineSessions")' formation-realm.json | tr '\n' ' '; echo
echo "-- utilisateurs exportes"
jq -r '.[] ' /dev/null 2>/dev/null
for f in formation-users-*.json; do jq -r '.users[] | "\(.username) credentials=\(.credentials|length)"' "$f"; done
echo "-- le secret hache d'un mot de passe est-il dans l'export ?"
jq -r '.users[0].credentials[0] | keys | join(" ")' formation-users-0.json
echo "-- cles de signature du realm (composants) dans l'export ?"
jq -r '.components["org.keycloak.keys.KeyProvider"][] | "\(.name) \(.providerId) privateKey=\(.config.privateKey != null)"' formation-realm.json
echo "-- realm master dans l'export ?"
ls | grep -c master || true
echo "-- taille de l'export : $(du -sk . | cut -f1) Ko ; dump : $(du -k $L/backup/keycloak-26.7.0.dump | cut -f1) Ko"
