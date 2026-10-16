#!/usr/bin/env bash
# Prépare le dossier du lab : certificat de test, secrets jetables, Compose, Caddyfile.
set -eu
D=/tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-production
L=$D/lab
rm -rf "$L"; mkdir -p "$L/certs" && cd "$L"

# 1. Certificat de test : une autorité locale, puis un certificat pour les deux noms.
openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj "/CN=Lab CA" \
  -keyout certs/ca.key -out certs/ca.crt 2>/dev/null
openssl req -newkey rsa:2048 -nodes -subj "/CN=auth.lab.test" \
  -keyout certs/lab.key -out certs/lab.csr 2>/dev/null
printf 'subjectAltName=DNS:auth.lab.test,DNS:admin.lab.test\n' > certs/san.cnf
openssl x509 -req -in certs/lab.csr -CA certs/ca.crt -CAkey certs/ca.key -CAcreateserial \
  -days 30 -extfile certs/san.cnf -out certs/lab.crt 2>/dev/null
openssl x509 -in certs/lab.crt -noout -ext subjectAltName

# 2. Secrets jetables, hors de tout fichier versionné.
umask 077
printf 'DB_PASSWORD=%s\nKC_ADMIN_PASSWORD=%s\n' "$(openssl rand -hex 16)" "$(openssl rand -hex 16)" > .env

cat > Caddyfile <<'EOF'
{
	auto_https off
}

# Adresse publique : seuls les chemins utiles aux applications.
auth.lab.test {
	tls /certs/lab.crt /certs/lab.key

	@master path /realms/master /realms/master/*
	handle @master {
		respond "Interdit" 403
	}

	@public path /realms/* /resources/* /.well-known/*
	handle @public {
		reverse_proxy keycloak:8080
	}

	handle {
		respond "Interdit" 403
	}
}

# Adresse d'administration : port distinct, publié sur la boucle locale seulement.
admin.lab.test:9443 {
	tls /certs/lab.crt /certs/lab.key
	reverse_proxy keycloak:8080
}
EOF

cat > compose.yaml <<'EOF'
name: prod

services:
  db:
    image: postgres:16-alpine@sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685
    environment:
      POSTGRES_DB: keycloak
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U keycloak -d keycloak"]
      interval: 5s
      timeout: 5s
      retries: 10

  keycloak:
    image: quay.io/keycloak/keycloak:26.7.0@sha256:0f198be292568439d700cdbfb893e69a6009bb43a94a06a945b1d3d506c76b13
    command: start
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://db:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: ${DB_PASSWORD}
      KC_HOSTNAME: https://auth.lab.test:18443
      KC_HOSTNAME_ADMIN: https://admin.lab.test:19443
      KC_HTTP_ENABLED: "true"
      KC_PROXY_HEADERS: xforwarded
      KC_HEALTH_ENABLED: "true"
      KC_METRICS_ENABLED: "true"
      KC_BOOTSTRAP_ADMIN_USERNAME: temp-admin
      KC_BOOTSTRAP_ADMIN_PASSWORD: ${KC_ADMIN_PASSWORD}
    depends_on:
      db:
        condition: service_healthy

  proxy:
    image: caddy:2.11.7-alpine@sha256:d8542f48d34a9cf4e4c11a478865229840e87e4c96ea3f439101f31a5d35f75f
    ports:
      - "127.0.0.1:18443:443"
      - "127.0.0.1:19443:9443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./certs/lab.crt:/certs/lab.crt:ro
      - ./certs/lab.key:/certs/lab.key:ro
    depends_on:
      - keycloak

volumes:
  pgdata:
EOF
docker compose config -q && echo "compose valide"
ss -ltn | grep -E ':(18443|19443)\b' && echo "PORT OCCUPE" || echo "ports 18443 et 19443 libres"
