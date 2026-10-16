#!/usr/bin/env bash
set -u
D=/tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-production
mkdir -p "$D/docs"
for p in server/hostname server/reverseproxy server/bootstrap-admin-recovery server/importExport server/configuration-production server/management-interface server/health server/containers server/db; do
  n=$(echo "$p" | tr '/' '_')
  curl -sL "https://www.keycloak.org/$p" -o "$D/docs/$n.html"
  echo "$p $(wc -c < "$D/docs/$n.html")"
done
curl -sL "https://www.keycloak.org/docs/latest/upgrading/index.html" -o "$D/docs/upgrading.html"
echo upgrading $(wc -c < "$D/docs/upgrading.html")
curl -sL "https://www.keycloak.org/docs/latest/release_notes/index.html" -o "$D/docs/release_notes.html"
echo notes $(wc -c < "$D/docs/release_notes.html")
for t in caddy:2 postgres:16-alpine curlimages/curl; do
  echo "== $t"; docker buildx imagetools inspect "$t" 2>&1 | head -12
done
