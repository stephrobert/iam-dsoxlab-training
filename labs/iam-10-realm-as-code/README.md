# Tutorial: where the secret ends up

This tutorial does not do the challenge. It describes one trivial resource, in
a scratch directory, and then goes looking for the secret afterwards. The whole
point of this lab is in that second step. Measured on this machine on
2026-10-16.

```bash
IDS=/opt/iam-lab/identifiants-lab.txt
URL=$(grep '^KEYCLOAK_URL=' $IDS | cut -d= -f2-)
PROVIDER=$(grep '^VERSION_PROVIDER=' $IDS | cut -d= -f2-)
echo "fournisseur sur $URL, provider a epingler : $PROVIDER"
```

The admin account is read straight out of the socle's environment file when it
is needed, and never copied into a shell variable of its own: a variable gets
echoed, logged, and remembered by your shell history.

## 1. A realm described in nine lines

```bash
sudo mkdir -p /tmp/tuto-10
sudo tee /tmp/tuto-10/provider.tf > /dev/null <<CONF
terraform {
  required_providers {
    keycloak = {
      source  = "keycloak/keycloak"
      version = "$PROVIDER"
    }
  }
}

provider "keycloak" {
  client_id = "admin-cli"
}

variable "le_secret" {
  type      = string
  sensitive = true
}
CONF
sudo tee /tmp/tuto-10/realm.tf > /dev/null <<'CONF'
resource "keycloak_realm" "essai" {
  realm   = "tuto-jetable"
  enabled = true
}

resource "keycloak_openid_client" "confidentielle" {
  realm_id              = keycloak_realm.essai.id
  client_id             = "appli-du-tuto"
  enabled               = true
  access_type           = "CONFIDENTIAL"
  client_secret         = var.le_secret
  standard_flow_enabled = true
  valid_redirect_uris   = ["http://localhost:9000/*"]
}
CONF
echo "deux fichiers ecrits"
```

Note what is not in those files: no URL, no account, no password. The provider
reads those from the environment, which is why the commands below pass them
that way instead of writing them down.

```bash
cd /tmp/tuto-10 && sudo terraform init -no-color 2>&1 | grep -E 'Installed|Error'
```

Read that line. It says `Installed keycloak/keycloak` and then
**« self-signed »**, with a key fingerprint. That is not a problem to solve:
the provider is published by the Keycloak project, not by HashiCorp, so it
carries its publisher's own signature.

## 2. Apply, with the secret passed through the environment

The secret is generated into a file that only root can read, and fed to
Terraform from there. Writing it on a command line would put it in your shell
history and in the process table.

```bash
sudo sh -c 'umask 077; openssl rand -hex 16 > /run/tuto-10-secret'
cd /tmp/tuto-10 && sudo sh -c '
  set -a
  . /opt/socle-iam/.env
  set +a
  KEYCLOAK_URL=http://127.0.0.1:8080 \
  KEYCLOAK_USER=$KC_BOOTSTRAP_ADMIN_USERNAME \
  KEYCLOAK_PASSWORD=$KC_BOOTSTRAP_ADMIN_PASSWORD \
  KEYCLOAK_REALM=master \
  TF_VAR_le_secret=$(cat /run/tuto-10-secret) \
  terraform apply -auto-approve -no-color' 2>&1 | tail -3
```

Two resources created, and the output said nothing about the secret:
`sensitive = true` did its job. Check the files you wrote, too:

```bash
cd /tmp/tuto-10 && sudo grep -l -F -f /run/tuto-10-secret ./*.tf 2>/dev/null \
  && echo "^ ce fichier .tf contient le secret" \
  || echo "aucun .tf ne contient le secret"
```

At this point everything looks right. The secret was generated, passed through
the environment, never written in a file you wrote, and masked in every output.

## 3. Now go and look at the state

```bash
cd /tmp/tuto-10
echo "occurrences du secret dans l etat : $(sudo grep -c -F -f /run/tuto-10-secret terraform.tfstate)"
sudo stat -c 'droits : %a  proprietaire : %U:%G' terraform.tfstate
sudo grep -o '"client_secret": "[^"]*"' terraform.tfstate \
  | sed 's/: ".*"/: "<le secret, en clair>"/'
```

The state file holds the secret in clear, in mode **644**, readable by every
account on the machine. Nothing warned you. `sensitive = true` governs what
Terraform prints, not what it stores.

This is the measurement that matters in this lab: **not writing a secret in
your code is not the same thing as not having it in clear on disk.** A
repository with impeccable `.tf` files and a committed state file has published
its secret.

Now tighten the state file, apply once more, and look at what sits next to it:

```bash
cd /tmp/tuto-10
sudo chmod 0600 terraform.tfstate
sudo sh -c '
  set -a
  . /opt/socle-iam/.env
  set +a
  cd /tmp/tuto-10
  KEYCLOAK_URL=http://127.0.0.1:8080 \
  KEYCLOAK_USER=$KC_BOOTSTRAP_ADMIN_USERNAME \
  KEYCLOAK_PASSWORD=$KC_BOOTSTRAP_ADMIN_PASSWORD \
  KEYCLOAK_REALM=master \
  TF_VAR_le_secret=$(cat /run/tuto-10-secret) \
  terraform apply -auto-approve -no-color > /dev/null 2>&1'
sudo stat -c '%n : %a' terraform.tfstate terraform.tfstate.backup
```

`terraform.tfstate` kept the `600` you gave it, because the tool writes into
the file that already exists. `terraform.tfstate.backup` is **recreated** on
every apply, with default permissions, and it holds the same secret. Tightening
a file that the tool recreates buys you exactly one apply.

What holds is the directory: whatever gets recreated inside it, nobody else
gets in.

## 4. Clean up

```bash
cd /tmp/tuto-10 && sudo sh -c '
  set -a
  . /opt/socle-iam/.env
  set +a
  cd /tmp/tuto-10
  KEYCLOAK_URL=http://127.0.0.1:8080 \
  KEYCLOAK_USER=$KC_BOOTSTRAP_ADMIN_USERNAME \
  KEYCLOAK_PASSWORD=$KC_BOOTSTRAP_ADMIN_PASSWORD \
  KEYCLOAK_REALM=master \
  TF_VAR_le_secret=$(cat /run/tuto-10-secret) \
  terraform destroy -auto-approve -no-color' 2>&1 | tail -2
cd /tmp && sudo rm -rf /tmp/tuto-10 && sudo rm -f /run/tuto-10-secret
echo "nettoye"
```

## What this leaves you

- a tool that manages something keeps a record of it, and that record contains
  everything it was given;
- « sensitive » usually describes what is displayed, rarely what is stored;
- permissions on a file an automated tool recreates are advisory; permissions
  on the directory are not.

```bash
dsoxlab challenge iam-10-realm-as-code
```
