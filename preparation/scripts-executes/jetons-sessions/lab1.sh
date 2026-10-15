#!/usr/bin/env bash
# Bloc 0a : démarrer Keycloak (identique à la leçon d'installation)
docker run -d --name keycloak -p 8080:8080 \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \
  -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:26.7.0@sha256:0f198be292568439d700cdbfb893e69a6009bb43a94a06a945b1d3d506c76b13 \
  start-dev
until curl -sf http://localhost:8080/realms/master >/dev/null; do sleep 2; done
echo "Keycloak prêt"
