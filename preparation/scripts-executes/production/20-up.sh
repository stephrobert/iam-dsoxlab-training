#!/usr/bin/env bash
set -u
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-production/lib.sh
docker compose up -d 2>&1 | tail -8
attendre
docker compose ps --format 'table {{.Service}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
echo "=== journal Keycloak (extraits)"
docker compose logs keycloak 2>&1 | grep -E "Keycloak .* started|Profile|production mode|KC-SERVICES0077|WARN" | cut -c1-260 | head -12
