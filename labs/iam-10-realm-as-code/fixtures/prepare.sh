#!/usr/bin/env bash
# Pose la situation du lab iam-10, et la retire avec `--nettoyer`.
#
# CE QU'IL POSE : Terraform épinglé, un répertoire de travail vide, et un
# cahier des charges précis dans le fichier d'identifiants. Rien d'autre.
#
# CE QU'IL NE FAIT PAS, parce que c'est le travail demandé : aucun fichier
# `.tf`, aucun realm. Il RETIRE d'ailleurs le realm et les fichiers qu'un
# passage précédent aurait laissés, sans quoi le lab serait vert avant d'avoir
# commencé.
#
# La trace va dans /var/log/dsoxlab-prepare.log, avec `set -x`, SUSPENDUE
# autour de chaque secret : ce journal est collecté par `dsoxlab support`.
set -euo pipefail

JOURNAL=/var/log/dsoxlab-prepare.log
exec > >(tee -a "$JOURNAL") 2>&1
set -x

KC=http://127.0.0.1:8080
SOCLE_ENV=/opt/socle-iam/.env
LAB=/opt/iam-lab
TRAVAIL=$LAB/realm-as-code
IDENTIFIANTS=$LAB/identifiants-lab.txt

#: Le realm que l'apprenant doit décrire et créer. Les tests le cherchent sous
#: ce nom, et le setup le retire au départ comme à l'arrivée.
REALM=as-code
#: Le cahier des charges, en dur ici et repris dans le fichier d'identifiants :
#: les tests le lisent là, pour qu'aucune valeur ne soit écrite deux fois.
DISPLAY_NAME="Realm decrit en code"
DUREE_JETON=600
ROLES="lecture ecriture"
GROUPE=equipe
CLIENT_PUBLIC=appli-publique-code
CLIENT_CONFIDENTIEL=appli-confidentielle-code
#: Le nom de la variable Terraform qui porte le secret du client
#: confidentiel. Il est IMPOSE parce que la notation rejoue le code de
#: l'apprenant : sans nom convenu, elle devrait deviner comment il a
#: appele ses variables, et un `plan` sans valeur sort en erreur.
VARIABLE_SECRET=secret_appli

TF_VERSION=${TF_VERSION:-}
PROVIDER_VERSION=${PROVIDER_VERSION:-}

if [ ! -r "$SOCLE_ENV" ]; then
  echo "ÉCHEC : $SOCLE_ENV est absent ou illisible. Le socle IAM n'est pas" >&2
  echo "installé, ou ce script tourne sous un compte hors du groupe docker." >&2
  exit 1
fi

set +x
KC_USER=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME=' "$SOCLE_ENV" | cut -d= -f2-)
KC_MDP=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD=' "$SOCLE_ENV" | cut -d= -f2-)
JETON=$(curl -sS --max-time 20 -X POST \
  "$KC/realms/master/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  -d "username=$KC_USER" -d "password=$KC_MDP" \
  | jq -r '.access_token // empty')
# Le test qui suit reste dans la zone NON tracée : `set -x` journaliserait
# la valeur du jeton, et ce fichier est collecté par `dsoxlab support`.
if [ -z "$JETON" ]; then
  echo "ÉCHEC : aucun jeton d'administration. Keycloak répond-il sur $KC ?" >&2
  exit 1
fi
set -x

admin() {
  set +x
  local m=$1 c=$2
  curl -sS --max-time 30 -X "$m" "$KC/admin/$c" -H "Authorization: Bearer $JETON"
  set -x
}

retirer_le_travail() {
  # Le realm décrit, et les fichiers de l'apprenant. Un realm qui survivrait
  # rendrait la moitié des tests verts sans travail.
  admin DELETE "realms/$REALM" > /dev/null 2>&1 || true
  if [ -d "$TRAVAIL" ]; then
    find "$TRAVAIL" -mindepth 1 -maxdepth 1 \
      \( -name '*.tf' -o -name '*.tfstate' -o -name '*.tfstate.backup' \
         -o -name '*.tfvars' -o -name '.terraform' -o -name '.terraform.lock.hcl' \
         -o -name '*.tfplan' \) -exec rm -rf {} + 2>/dev/null || true
  fi
  return 0
}

# ─── Mode nettoyage, appelé par cleanup.yaml ──────────────────────────────────
if [ "${1:-}" = "--nettoyer" ]; then
  retirer_le_travail
  rm -f "$IDENTIFIANTS"
  rmdir "$TRAVAIL" 2>/dev/null || true
  echo "nettoyage du lab iam-10 terminé"
  exit 0
fi

# ─── À partir d'ici, les versions sont indispensables ─────────────────────────
for variable in TF_VERSION PROVIDER_VERSION; do
  if [ -z "${!variable}" ]; then
    echo "ÉCHEC : $variable n'est pas fournie. Le setup la lit dans" >&2
    echo "shared/images.yml et la passe en variable d'environnement." >&2
    exit 1
  fi
done

retirer_le_travail
mkdir -p "$TRAVAIL"
chown student:docker "$TRAVAIL"
chmod 0775 "$TRAVAIL"

# ─── 1. Terraform, épinglé ────────────────────────────────────────────────────
# `unzip` n'est pas dans l'image de base de la machine, et l'archive de
# Terraform en a besoin. Mesuré le 2026-10-16 : les deux étaient absents.
if ! command -v unzip > /dev/null 2>&1; then
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq unzip > /dev/null
fi

# `| head -1` sous `set -o pipefail` est un piège : `head` ferme le tuyau
# dès la première ligne, terraform meurt sur SIGPIPE, le pipeline rend 141
# et `set -e` tue le script. Vécu le 2026-10-16, et d'autant plus vicieux
# que cela dépend de la taille du tampon : la même commande passe parfois.
# La sortie est donc lue en entier, puis découpée.
VERSION_BRUTE=$(terraform version 2>/dev/null || true)
INSTALLEE=$(printf '%s\n' "$VERSION_BRUTE" | awk 'NR==1{print $2}' | tr -d v)
if [ "$INSTALLEE" != "$TF_VERSION" ]; then
  curl -sSL --max-time 300 \
    "https://releases.hashicorp.com/terraform/${TF_VERSION}/terraform_${TF_VERSION}_linux_amd64.zip" \
    -o /tmp/terraform.zip
  unzip -oq /tmp/terraform.zip -d /usr/local/bin
  chmod 0755 /usr/local/bin/terraform
  rm -f /tmp/terraform.zip
fi
printf '%s\n' "$(terraform version | awk 'NR==1')"

# ─── 2. Ce que l'apprenant doit savoir pour commencer ─────────────────────────
set +x
{
  echo "# Posé par le setup du lab iam-10. Jetable."
  echo "# Le CAHIER DES CHARGES du realm à décrire est ici : les tests lisent"
  echo "# ces valeurs, ils ne les portent pas en dur."
  echo "KEYCLOAK_URL=${KC}"
  echo "REALM_A_DECRIRE=${REALM}"
  echo "DISPLAY_NAME_ATTENDU=${DISPLAY_NAME}"
  echo "DUREE_JETON_ATTENDUE=${DUREE_JETON}"
  echo "ROLES_ATTENDUS=${ROLES}"
  echo "GROUPE_ATTENDU=${GROUPE}"
  echo "CLIENT_PUBLIC_ATTENDU=${CLIENT_PUBLIC}"
  echo "CLIENT_CONFIDENTIEL_ATTENDU=${CLIENT_CONFIDENTIEL}"
  echo "VARIABLE_SECRET_ATTENDUE=${VARIABLE_SECRET}"
  echo "REPERTOIRE_TRAVAIL=${TRAVAIL}"
  echo "VERSION_TERRAFORM=${TF_VERSION}"
  echo "VERSION_PROVIDER=${PROVIDER_VERSION}"
  echo "# Le compte d'administration du socle, que le provider doit lire dans"
  echo "# l'ENVIRONNEMENT et non dans un fichier :"
  echo "#   export KEYCLOAK_URL=${KC}"
  echo "#   export KEYCLOAK_USER=... KEYCLOAK_PASSWORD=... (voir ${SOCLE_ENV})"
  echo "#   export KEYCLOAK_REALM=master"
  echo "ENV_DU_SOCLE=${SOCLE_ENV}"
} > "$IDENTIFIANTS"
chown student:docker "$IDENTIFIANTS"
chmod 0640 "$IDENTIFIANTS"
set -x

# ─── 3. Contrôler l'état posé ─────────────────────────────────────────────────
# Sans ces contrôles, un lab parti d'un travail déjà fait serait vert avant
# d'avoir commencé.
# La trace est SUSPENDUE autour de ce curl : il porte le jeton
# d'administration dans un en-tête, et ce journal est collecté par
# `dsoxlab support`. Un secret tracé est un secret publié.
set +x
CODE_REALM=$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' \
  "$KC/admin/realms/$REALM" -H "Authorization: Bearer $JETON" || true)
set -x
NB_TF=$(find "$TRAVAIL" -maxdepth 1 -name '*.tf' | wc -l)
NB_STATE=$(find "$TRAVAIL" -maxdepth 1 -name '*.tfstate' | wc -l)

if [ "$CODE_REALM" != "404" ] || [ "$NB_TF" -ne 0 ] || [ "$NB_STATE" -ne 0 ]; then
  echo "ÉCHEC : la situation de départ n'est pas celle attendue." >&2
  echo "code_realm=$CODE_REALM (404 attendu) fichiers_tf=$NB_TF (0)" >&2
  echo "fichiers_etat=$NB_STATE (0)" >&2
  exit 1
fi

set +x
echo "Situation posée : Terraform $TF_VERSION installé, répertoire de travail"
echo "vide dans $TRAVAIL, et aucun realm « $REALM » sur $KC."
echo "Le cahier des charges est dans $IDENTIFIANTS"
