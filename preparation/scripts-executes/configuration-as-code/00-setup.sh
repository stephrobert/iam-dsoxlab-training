#!/usr/bin/env bash
# Démarre Keycloak 26.7.0 jetable et écrit les fichiers Terraform de la leçon.
set -euo pipefail
D=/tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-cac
docker run -d --name cac-keycloak -p 127.0.0.1:18180:8080 \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \
  -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:26.7.0@sha256:0f198be292568439d700cdbfb893e69a6009bb43a94a06a945b1d3d506c76b13 \
  start-dev
until curl -sf http://localhost:18180/realms/master >/dev/null; do sleep 3; done
echo up
mkdir -p "$D/lab"
cd "$D/lab"
cat > versions.tf <<'EOF'
terraform {
  required_version = "= 1.16.1"

  required_providers {
    keycloak = {
      source  = "keycloak/keycloak"
      version = "= 5.10.0"
    }
  }
}

provider "keycloak" {
  # URL, compte et mot de passe viennent de l'environnement :
  # KEYCLOAK_URL, KEYCLOAK_CLIENT_ID, KEYCLOAK_USER, KEYCLOAK_PASSWORD
}
EOF
cat > variables.tf <<'EOF'
variable "realm_name" {
  description = "Nom du realm géré par ce dossier"
  type        = string
  default     = "formation"

  validation {
    condition     = var.realm_name != "master"
    error_message = "Refus : ce dossier ne doit jamais gérer le realm master."
  }
}

variable "boutique_secret" {
  description = "Secret du client boutique, fourni par TF_VAR_boutique_secret"
  type        = string
  sensitive   = true
}
EOF
cat > main.tf <<'EOF'
resource "keycloak_realm" "formation" {
  realm                    = var.realm_name
  enabled                  = true
  display_name             = "Formation IAM"
  access_token_lifespan    = "10m"
  ssl_required             = "external"
  login_with_email_allowed = true
}

resource "keycloak_role" "lecteur" {
  realm_id    = keycloak_realm.formation.id
  name        = "lecteur"
  description = "Consulte le catalogue"
}

resource "keycloak_role" "editeur" {
  realm_id    = keycloak_realm.formation.id
  name        = "editeur"
  description = "Modifie le catalogue"
}

resource "keycloak_group" "equipe_boutique" {
  realm_id = keycloak_realm.formation.id
  name     = "equipe-boutique"
}

resource "keycloak_group_roles" "equipe_boutique" {
  realm_id = keycloak_realm.formation.id
  group_id = keycloak_group.equipe_boutique.id
  role_ids = [keycloak_role.lecteur.id]
}

resource "keycloak_openid_client" "boutique" {
  realm_id                     = keycloak_realm.formation.id
  client_id                    = "boutique"
  name                         = "Boutique"
  access_type                  = "CONFIDENTIAL"
  client_secret                = var.boutique_secret
  standard_flow_enabled        = true
  direct_access_grants_enabled = false
  valid_redirect_uris          = ["https://boutique.exemple.fr/callback"]
}
EOF
cat > env.sh <<'EOF'
export KEYCLOAK_URL=http://localhost:18180
export KEYCLOAK_CLIENT_ID=admin-cli
export KEYCLOAK_USER=admin
export KEYCLOAK_PASSWORD=admin
export TF_VAR_boutique_secret="$(openssl rand -hex 16)"
EOF
source env.sh
terraform fmt
terraform init 2>&1 | tail -15
