#!/usr/bin/env bash
set -u
KC=quay.io/keycloak/keycloak:26.7.0@sha256:0f198be292568439d700cdbfb893e69a6009bb43a94a06a945b1d3d506c76b13
echo "##### piege A : start sans hostname (HTTP active, pas de TLS)"
docker run --rm -e KC_BOOTSTRAP_ADMIN_USERNAME=x -e KC_BOOTSTRAP_ADMIN_PASSWORD=y $KC start --db=dev-mem --http-enabled=true 2>&1 | grep -E "ERROR|hostname|started in" | cut -c1-300 | head -4
echo "##### piege B : start sans hostname ni HTTP ni certificat"
docker run --rm $KC start --db=dev-mem --hostname=https://auth.lab.test 2>&1 | grep -E "ERROR|HTTPS|Key material|started in" | cut -c1-300 | head -4
echo "##### piege C : start-dev (avertissement du journal)"
docker run -d --name prod-dev -e KC_BOOTSTRAP_ADMIN_USERNAME=x -e KC_BOOTSTRAP_ADMIN_PASSWORD=y $KC start-dev >/dev/null
sleep 25
docker logs prod-dev 2>&1 | grep -E "DO NOT use|started in" | cut -c1-260 | head -3
docker rm -f prod-dev >/dev/null
