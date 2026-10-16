#!/usr/bin/env bash
# Fonctions communes (source). Aucune ne s'appelle k.
D=/tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-production
L=$D/lab
cd "$L"
CA=$L/certs/ca.crt
PUB=https://auth.lab.test:18443
ADM=https://admin.lab.test:19443
# curl depuis l'hote : resolution des deux noms vers la boucle locale, CA de test
cpub() { curl -sS --cacert "$CA" --resolve auth.lab.test:18443:127.0.0.1 "$@"; }
cadm() { curl -sS --cacert "$CA" --resolve admin.lab.test:19443:127.0.0.1 "$@"; }
# curl depuis le reseau du conteneur Keycloak (port de gestion 9000)
cmgmt() { docker run --rm --network container:"$(docker compose ps -q keycloak)" curlimages/curl:8.23.0@sha256:a134550be58ab783810e613ae96fd253c38f7bdd16d9bf9be350700c7a29ac06 -sS "$@"; }
kcadm() { docker compose exec -T keycloak /opt/keycloak/bin/kcadm.sh "$@"; }
attendre() {
  local i
  for i in $(seq 1 90); do
    if cmgmt -o /dev/null -f http://localhost:9000/health/ready 2>/dev/null; then echo "pret apres ${i}x2s"; return 0; fi
    sleep 2
  done
  echo "TIMEOUT"; docker compose logs --tail 30 keycloak; return 1
}
