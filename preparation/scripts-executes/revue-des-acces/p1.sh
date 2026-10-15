#!/usr/bin/env bash
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/lab-revue/common.sh
docker network create iam-lab
docker run -d --name mailpit --network iam-lab -p 8025:8025 \
  axllent/mailpit:v1.30.4@sha256:5a49a77c5bdbe7c5474450b4f46348d09949df3695257729c93a30369382d4f6
docker run -d --name keycloak --network iam-lab -p 8080:8080 \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \
  -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:26.8.1@sha256:79c623a22abacf3fe6c00a5fb30f5b7843d717b234033b80995891c06116d244 \
  start-dev --spi-events-listener--workflow-event-listener--step-runner-task-interval=5s \
  --log-level=INFO,org.keycloak.models.workflow:debug
until curl -sf http://localhost:8080/realms/master >/dev/null; do sleep 2; done
kcadm config credentials --server http://localhost:8080 --realm master --user admin --password admin
kcadm create realms -s realm=entreprise -s enabled=true
echo ---log; docker logs keycloak 2>&1 | grep 'Workflow runner' | cut -c1-200
