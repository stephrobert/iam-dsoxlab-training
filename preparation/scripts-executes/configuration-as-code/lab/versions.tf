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
