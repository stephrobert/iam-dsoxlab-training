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
