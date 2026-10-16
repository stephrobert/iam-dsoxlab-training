#!/usr/bin/env bash
set -u
D=/tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-production
KC26=quay.io/keycloak/keycloak:26.7.0@sha256:0f198be292568439d700cdbfb893e69a6009bb43a94a06a945b1d3d506c76b13
docker compose version
openssl version
docker pull "$KC26" | tail -2
docker pull postgres:16-alpine@sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685 | tail -2
docker pull caddy:2.11.7-alpine@sha256:d8542f48d34a9cf4e4c11a478865229840e87e4c96ea3f439101f31a5d35f75f | tail -2
docker pull curlimages/curl:8.23.0@sha256:a134550be58ab783810e613ae96fd253c38f7bdd16d9bf9be350700c7a29ac06 | tail -2
echo "=== start --help (options ciblées)"
docker run --rm "$KC26" start --help-all 2>&1 | grep -E -A3 '^\s*--(hostname|hostname-admin|proxy-headers|http-enabled|health-enabled|metrics-enabled|hostname-strict|bootstrap-admin-username)\b' | head -80
echo "=== bootstrap-admin --help"
docker run --rm "$KC26" bootstrap-admin --help 2>&1 | head -40
docker run --rm "$KC26" bootstrap-admin user --help 2>&1 | head -40
echo "=== export --help"
docker run --rm "$KC26" export --help 2>&1 | grep -E -A2 '^\s*--(dir|file|realm|users|users-per-file)\b'
