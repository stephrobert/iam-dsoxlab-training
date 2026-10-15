#!/usr/bin/env bash
cd /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/lab-revue
kcadm() { docker exec keycloak /opt/keycloak/bin/kcadm.sh "$@"; }
KC=http://localhost:8080; SC=$KC/realms/entreprise/scim/v2
