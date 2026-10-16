#!/usr/bin/env bash
# Pose la situation du lab iam-04, et la retire avec `--nettoyer`.
#
# CE QUE CE SCRIPT NE FAIT PAS : déclarer le client OIDC. C'est le travail
# demandé. Il pose tout le reste, pour que l'apprenant n'ait à s'occuper que du
# fournisseur d'identité et de l'application.
#
# Un passage précédent laisse un client et une configuration : les deux sont
# retirés ici. Sans cela, le lab serait noté sur un travail déjà fait, et la
# note ne dirait rien de l'apprenant.
#
# La trace va dans /var/log/dsoxlab-prepare.log, avec `set -x` : dsoxlab ne rend
# que « non-zero return code » quand un script de mise en situation échoue, et
# c'est ce fichier que le validateur relit pour dire pourquoi.
set -euo pipefail

JOURNAL=/var/log/dsoxlab-prepare.log
exec > >(tee -a "$JOURNAL") 2>&1
set -x

KC=http://127.0.0.1:8080
REALM=formation
CLIENT=appli-notes
APPLI=/opt/iam-lab/appli-temoin
PORT_TEMOIN=9080
IDENTIFIANTS=/opt/iam-lab/identifiants-lab.txt
SECRETS=/opt/socle-iam/secrets.yml

# ─── Le socle doit être là ────────────────────────────────────────────────────
# Un lab qui part sans socle échoue plus tard, sur un test, et l'apprenant
# cherche alors la cause dans son travail. Mieux vaut refuser tout de suite en
# nommant ce qui manque.
if [ ! -r "$SECRETS" ]; then
  echo "ÉCHEC : $SECRETS est absent ou illisible. Le socle IAM n'est pas" >&2
  echo "installé, ou ce script tourne sous un compte qui n'est pas dans le" >&2
  echo "groupe docker. Le setup du lab inclut shared/socle-iam.yml : si le" >&2
  echo "socle manque, c'est l'inclusion qui a échoué, pas ce script." >&2
  exit 1
fi

jeton_admin() {
  local utilisateur mot_de_passe jeton
  utilisateur=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME:' "$SECRETS" | cut -d'"' -f2)
  mot_de_passe=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD:' "$SECRETS" | cut -d'"' -f2)
  jeton=$(curl -sS --max-time 20 -X POST \
    "$KC/realms/master/protocol/openid-connect/token" \
    -d grant_type=password -d client_id=admin-cli \
    -d "username=$utilisateur" -d "password=$mot_de_passe" \
    | jq -r '.access_token // empty')
  if [ -z "$jeton" ]; then
    echo "ÉCHEC : aucun jeton d'administration. Keycloak répond-il sur $KC ?" >&2
    return 1
  fi
  printf '%s' "$jeton"
}

retirer_le_client() {
  local jeton=$1 identifiant
  identifiant=$(curl -sS --max-time 20 \
    "$KC/admin/realms/$REALM/clients?clientId=$CLIENT" \
    -H "Authorization: Bearer $jeton" | jq -r '.[0].id // empty')
  if [ -n "$identifiant" ]; then
    curl -sS --max-time 20 -o /dev/null -X DELETE \
      "$KC/admin/realms/$REALM/clients/$identifiant" \
      -H "Authorization: Bearer $jeton"
  fi
}

arreter_le_temoin() {
  # Par le PORT, et non par la ligne de commande.
  #
  # Mesuré le 2026-10-16 : un `pkill -f "$APPLI/appli.py"` ne trouve rien
  # quand le témoin a été lancé depuis son répertoire, sa ligne de commande
  # étant alors `./.venv/bin/python appli.py`. Le setup échouait ensuite sur
  # « le port 9080 reste occupé », sans dire que le motif était en cause.
  /opt/iam-lab/outils/arreter-temoin.sh "$PORT_TEMOIN"
  rm -f "$APPLI/configuration.json" "$APPLI/temoin.log"
}

JETON=$(jeton_admin)

# ─── Mode nettoyage, appelé par cleanup.yaml ──────────────────────────────────
if [ "${1:-}" = "--nettoyer" ]; then
  arreter_le_temoin
  retirer_le_client "$JETON"
  ID_ALICE=$(curl -sS --max-time 20 \
    "$KC/admin/realms/$REALM/users?username=alice&exact=true" \
    -H "Authorization: Bearer $JETON" | jq -r '.[0].id // empty')
  if [ -n "$ID_ALICE" ]; then
    curl -sS --max-time 20 -o /dev/null -X DELETE \
      "$KC/admin/realms/$REALM/users/$ID_ALICE" \
      -H "Authorization: Bearer $JETON"
  fi
  rm -f "$IDENTIFIANTS"
  echo "nettoyage du lab iam-04 terminé"
  exit 0
fi

# ─── Le compte humain du lab ──────────────────────────────────────────────────
# `openssl rand`, et SURTOUT PAS `tr -dc < /dev/urandom | head -c 24` : sous
# `set -o pipefail`, ce pipeline rend un code non nul parce que `head` ferme le
# tube et que `tr` reçoit SIGPIPE. L'affectation réussit, puis `set -e` tue le
# script, et la trace montre la variable affectée : on cherche alors la cause
# dans la commande suivante, qui n'a jamais tourné.
SECRET_DU_COMPTE=$(openssl rand -hex 12)

# IDEMPOTENT, ET LE SECRET EST TOUJOURS REPOSÉ.
#
# Mesuré le 2026-10-16 : un POST suivi d'un `|| true` avale le 409 d'un compte
# déjà créé, et le secret reste celui du premier passage. Le flux échoue alors
# sur « Invalid username or password », ce qui ressemble trait pour trait à un
# client mal déclaré, alors que le client est bon.
curl -sS --max-time 20 -o /dev/null -w 'creation alice: HTTP %{http_code}\n' \
  -X POST "$KC/admin/realms/$REALM/users" \
  -H "Authorization: Bearer $JETON" -H 'Content-Type: application/json' \
  -d "$(jq -nc '{username:"alice", enabled:true, emailVerified:true,
        firstName:"Alice", lastName:"Martin", email:"alice@formation.lab"}')"

ID_ALICE=$(curl -sS --max-time 20 \
  "$KC/admin/realms/$REALM/users?username=alice&exact=true" \
  -H "Authorization: Bearer $JETON" | jq -r '.[0].id // empty')
if [ -z "$ID_ALICE" ]; then
  echo "ÉCHEC : alice n'existe pas après sa création." >&2
  exit 1
fi

curl -sS --max-time 20 -o /dev/null -X PUT \
  "$KC/admin/realms/$REALM/users/$ID_ALICE/reset-password" \
  -H "Authorization: Bearer $JETON" -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg m "$SECRET_DU_COMPTE" \
        '{type:"password", value:$m, temporary:false}')"

# ─── Retirer tout travail d'un passage précédent ──────────────────────────────
retirer_le_client "$JETON"
arreter_le_temoin

# ─── Les identifiants, là où l'apprenant ET les tests les lisent ──────────────
# En clair sur la machine du lab, ce qui est assumé : c'est une machine jetable
# dont le secret est tiré à chaque mise en situation. Rien de cela n'est
# versionné.
{
  echo "# Posé par le setup du lab iam-04. Jetable, régénéré à chaque run."
  echo "REALM=${REALM}"
  echo "UTILISATEUR=alice"
  printf 'MOT_DE_PASSE=%s\n' "$SECRET_DU_COMPTE"
} > "$IDENTIFIANTS"
chown student:docker "$IDENTIFIANTS"
chmod 0640 "$IDENTIFIANTS"

# ─── Le port du témoin doit être libre ────────────────────────────────────────
# Le contrôle porte sur l'état, pas sur le fait que `pkill` a rendu 0 : un
# processus en cours d'arrêt tient encore son port, et l'apprenant verrait un
# « address already in use » qui ne dirait rien de son travail.
# L'attente vit dans `arreter-temoin.sh`, qui sort en 1 si le port reste pris.
# La refaire ici donnerait deux endroits à corriger pour une seule règle.

set +x
echo "Situation posée : realm ${REALM}, compte alice, aucun client déclaré."
echo "Identifiants dans ${IDENTIFIANTS}"
