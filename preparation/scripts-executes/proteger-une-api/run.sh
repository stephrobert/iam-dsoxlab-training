#!/usr/bin/env bash
# Rejoue les blocs de la leçon dans un seul terminal (fonctions partagées).
cd "$(dirname "$0")"
set -u
docker rm -f keycloak >/dev/null 2>&1
for b in blocs/01-keycloak.sh blocs/02-api-scopes.sh blocs/03-helpers.sh blocs/04-api-run.sh; do
  echo "##### $b"; source "$b"
done
sleep 3
for b in blocs/05-refus.sh blocs/06-service.sh blocs/07-introspection.sh blocs/08-device.sh blocs/09-exchange.sh; do
  echo "##### $b"; source "$b"
done
date +%T > fin.txt
echo "##### attente expiration"
sleep 310
appel "$API" -H "Authorization: Bearer $SERVICE"
echo "#### grep secret"
grep -rlF "$(cat secret-sauvegarde.txt)" . --exclude-dir=.venv --exclude=secret-sauvegarde.txt || echo "secret absent des autres fichiers"
echo "#### cleanup"
pkill -f ".venv/bin/python api.py"
docker rm -f keycloak
