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
