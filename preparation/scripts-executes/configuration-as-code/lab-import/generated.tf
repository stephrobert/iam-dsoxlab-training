# __generated__ by Terraform
# Please review these resources and move them into your main configuration files.

# __generated__ by Terraform from "formation"
resource "keycloak_realm" "formation" {
  access_code_lifespan                     = "1m0s"
  access_code_lifespan_login               = "30m0s"
  access_code_lifespan_user_action         = "5m0s"
  access_token_lifespan                    = "10m0s"
  access_token_lifespan_for_implicit_flow  = "15m0s"
  account_theme                            = null
  action_token_generated_by_admin_lifespan = "12h0m0s"
  action_token_generated_by_user_lifespan  = "5m0s"
  admin_permissions_enabled                = false
  admin_theme                              = null
  attributes                               = {}
  browser_flow                             = "browser"
  client_authentication_flow               = "clients"
  client_session_idle_timeout              = "0s"
  client_session_max_lifespan              = "0s"
  default_default_client_scopes            = []
  default_optional_client_scopes           = []
  default_signature_algorithm              = null
  direct_grant_flow                        = "direct grant"
  display_name                             = "Formation IAM"
  display_name_html                        = null
  docker_authentication_flow               = "docker auth"
  duplicate_emails_allowed                 = false
  edit_username_allowed                    = false
  email_theme                              = null
  enabled                                  = true
  first_broker_login_flow                  = "first broker login"
  internal_id                              = "formation"
  login_theme                              = null
  login_with_email_allowed                 = true
  oauth2_device_code_lifespan              = "10m0s"
  oauth2_device_polling_interval           = 5
  offline_session_idle_timeout             = "720h0m0s"
  offline_session_max_lifespan             = "1440h0m0s"
  offline_session_max_lifespan_enabled     = false
  organizations_enabled                    = false
  password_policy                          = null
  realm                                    = "formation"
  refresh_token_max_reuse                  = 0
  registration_allowed                     = false
  registration_email_as_username           = false
  registration_flow                        = "registration"
  remember_me                              = false
  reset_credentials_flow                   = "reset credentials"
  reset_password_allowed                   = false
  revoke_refresh_token                     = false
  ssl_required                             = "external"
  sso_session_idle_timeout                 = "30m0s"
  sso_session_idle_timeout_remember_me     = "0s"
  sso_session_max_lifespan                 = "10h0m0s"
  sso_session_max_lifespan_remember_me     = "0s"
  terraform_deletion_protection            = false
  user_managed_access                      = false
  verify_email                             = false
  otp_policy {
    algorithm         = "HmacSHA1"
    code_reusable     = false
    digits            = 6
    initial_counter   = 0
    look_ahead_window = 1
    period            = 30
    type              = "totp"
  }
  web_authn_passwordless_policy {
    acceptable_aaguids                = []
    attestation_conveyance_preference = "not specified"
    authenticator_attachment          = "not specified"
    avoid_same_authenticator_register = false
    create_timeout                    = 0
    discoverable_credential           = "required"
    extra_origins                     = []
    passwordless_passkeys_enabled     = false
    relying_party_entity_name         = "keycloak"
    relying_party_id                  = null
    signature_algorithms              = ["ES256", "RS256"]
    user_verification_requirement     = "required"
  }
  web_authn_policy {
    acceptable_aaguids                = []
    attestation_conveyance_preference = "not specified"
    authenticator_attachment          = "not specified"
    avoid_same_authenticator_register = false
    create_timeout                    = 0
    discoverable_credential           = "not specified"
    extra_origins                     = []
    relying_party_entity_name         = "keycloak"
    relying_party_id                  = null
    signature_algorithms              = ["ES256", "RS256"]
    user_verification_requirement     = "not specified"
  }
}

# __generated__ by Terraform from "formation/07bc048c-18ab-466e-993b-4a4188a2ed56"
resource "keycloak_openid_client" "boutique" {
  access_type                                    = "CONFIDENTIAL"
  admin_url                                      = null
  allow_refresh_token_in_standard_token_exchange = null
  always_display_in_console                      = false
  backchannel_logout_revoke_offline_sessions     = false
  backchannel_logout_session_required            = true
  backchannel_logout_url                         = null
  base_url                                       = null
  client_authenticator_type                      = "client-secret"
  client_id                                      = "boutique"
  client_secret                                  = null # sensitive
  client_secret_regenerate_when_changed          = null
  client_secret_wo                               = null # sensitive
  client_secret_wo_version                       = null
  consent_required                               = false
  consent_screen_text                            = null
  description                                    = null
  direct_access_grants_enabled                   = false
  display_on_consent_screen                      = false
  enabled                                        = true
  extra_config                                   = {}
  frontchannel_logout_enabled                    = false
  frontchannel_logout_url                        = null
  full_scope_allowed                             = true
  implicit_flow_enabled                          = false
  import                                         = false
  login_theme                                    = null
  name                                           = "Boutique"
  oauth2_device_authorization_grant_enabled      = false
  oauth2_device_code_lifespan                    = null
  oauth2_device_polling_interval                 = null
  oauth2_jwt_authorization_grant_enabled         = false
  oauth2_jwt_authorization_grant_idp             = null
  pkce_code_challenge_method                     = null
  realm_id                                       = "formation"
  require_dpop_bound_tokens                      = false
  root_url                                       = null
  service_accounts_enabled                       = false
  standard_flow_enabled                          = true
  standard_token_exchange_enabled                = false
  use_refresh_tokens                             = true
  use_refresh_tokens_client_credentials          = false
  valid_post_logout_redirect_uris                = []
  valid_redirect_uris                            = ["https://boutique.exemple.fr/callback"]
  web_origins                                    = []
}
