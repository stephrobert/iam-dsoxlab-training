# Tutoriel : où le secret finit

Ce tutoriel ne fait pas le challenge. Il décrit une ressource triviale, dans un
répertoire jetable, puis va chercher le secret après coup. Tout le propos de ce
lab est dans cette seconde étape. Mesuré sur cette machine le 2026-10-16.

```bash
IDS=/opt/iam-lab/identifiants-lab.txt
URL=$(grep '^KEYCLOAK_URL=' $IDS | cut -d= -f2-)
PROVIDER=$(grep '^VERSION_PROVIDER=' $IDS | cut -d= -f2-)
echo "fournisseur sur $URL, provider a epingler : $PROVIDER"
```

Le compte d'administration est lu directement dans le fichier d'environnement
du socle au moment où il sert, et jamais recopié dans une variable à lui : une
variable se fait afficher, journaliser, et retenir par l'historique de votre
shell.

## 1. Un realm décrit en neuf lignes

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

Remarquez ce qui n'est pas dans ces fichiers : aucune URL, aucun compte, aucun
mot de passe. Le provider les lit dans l'environnement, et c'est pour cela que
les commandes ci-dessous les lui passent ainsi au lieu de les écrire.

```bash
cd /tmp/tuto-10 && sudo terraform init -no-color 2>&1 | grep -E 'Installed|Error'
```

Lisez cette ligne. Elle dit `Installed keycloak/keycloak` puis
**« self-signed »**, avec l'empreinte d'une clef. Ce n'est pas un problème à
régler : le provider est publié par le projet Keycloak, et non par HashiCorp,
il porte donc la signature de son propre éditeur.

## 2. Appliquer, avec le secret passé par l'environnement

Le secret est tiré dans un fichier que seul root peut lire, et fourni à
Terraform depuis là. L'écrire sur une ligne de commande le mettrait dans
l'historique de votre shell et dans la table des processus.

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

Deux ressources créées, et la sortie n'a rien dit du secret : `sensitive = true`
a fait son travail. Vérifiez aussi les fichiers que vous avez écrits :

```bash
cd /tmp/tuto-10 && sudo grep -l -F -f /run/tuto-10-secret ./*.tf 2>/dev/null \
  && echo "^ ce fichier .tf contient le secret" \
  || echo "aucun .tf ne contient le secret"
```

À ce stade, tout a l'air juste. Le secret a été tiré, passé par
l'environnement, jamais écrit dans un fichier que vous avez rédigé, et masqué
dans toutes les sorties.

## 3. Allez maintenant regarder l'état

```bash
cd /tmp/tuto-10
echo "occurrences du secret dans l etat : $(sudo grep -c -F -f /run/tuto-10-secret terraform.tfstate)"
sudo stat -c 'droits : %a  proprietaire : %U:%G' terraform.tfstate
sudo grep -o '"client_secret": "[^"]*"' terraform.tfstate \
  | sed 's/: ".*"/: "<le secret, en clair>"/'
```

Le fichier d'état porte le secret en clair, en mode **644**, lisible par tous
les comptes de la machine. Rien ne vous a averti. `sensitive = true` gouverne
ce que Terraform affiche, pas ce qu'il stocke.

C'est la mesure qui compte dans ce lab : **ne pas écrire un secret dans son
code n'est pas la même chose que ne pas l'avoir en clair sur le disque.** Un
dépôt aux fichiers `.tf` impeccables et au fichier d'état commité a publié son
secret.

Resserrez maintenant le fichier d'état, appliquez une fois de plus, et regardez
ce qui se trouve à côté :

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

`terraform.tfstate` a gardé le `600` que vous lui avez donné, parce que l'outil
écrit dans le fichier qui existe déjà. `terraform.tfstate.backup` est
**recréé** à chaque application, avec les droits par défaut, et il porte le même
secret. Resserrer un fichier que l'outil recrée vous achète exactement une
application.

Ce qui tient, c'est le répertoire : quoi qu'il s'y recrée, personne d'autre
n'entre.

## 4. Nettoyer

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

## Ce que cela vous laisse

- un outil qui gère quelque chose en garde une trace, et cette trace contient
  tout ce qu'on lui a donné ;
- « sensible » décrit d'ordinaire ce qui s'affiche, rarement ce qui se stocke ;
- les droits d'un fichier qu'un outil automatique recrée sont une indication ;
  ceux du répertoire n'en sont pas une.

```bash
dsoxlab challenge iam-10-realm-as-code
```
