#!/usr/bin/env bash
# Pose la situation : un repertoire de travail vide, et rien qui tourne.
#
# Ce lab demande d'INSTALLER Keycloak. La situation de depart est donc
# l'absence de Keycloak, ce qui parait evident mais ne l'est pas : la machine
# peut porter un socle d'un autre lab joue avant celui-ci, et les labs
# partagent la meme VM.
#
# Sans ce menage, l'apprenant trouverait un Keycloak deja debout et ses tests
# passeraient AVANT son travail, ce qui est le defaut le plus couteux du
# domaine.
set -euo pipefail
# La trace complete va dans un journal sur la machine : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit ce
# fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

TRAVAIL=/opt/keycloak-lab

# Un socle IAM laisse par un autre lab doit partir, VOLUMES COMPRIS : une base
# qui survivrait porterait un realm `formation` que ce lab demande de creer, et
# son test de persistance serait vert sans rien faire.
if [[ -f /opt/socle-iam/compose.yaml ]]; then
  (cd /opt/socle-iam && docker compose --env-file .env down -v --remove-orphans) || true
fi

# Ce que l'apprenant a pu laisser d'un passage precedent de CE lab.
if [[ -f "$TRAVAIL/compose.yaml" ]] || [[ -f "$TRAVAIL/compose.yml" ]]; then
  (cd "$TRAVAIL" && docker compose down -v --remove-orphans) || true
fi

# Les conteneurs orphelins que ni l'un ni l'autre ne reprendrait, par exemple
# un `docker run` lance a la main pendant une recherche.
for nom in $(docker ps -aq --filter 'ancestor=quay.io/keycloak/keycloak' 2>/dev/null); do
  docker rm -f "$nom" || true
done

rm -rf "$TRAVAIL"
install -d -m 0775 -o student -g docker "$TRAVAIL"

# LES IDENTIFIANTS DE L'ADMINISTRATEUR SONT IMPOSES, ET GENERES.
#
# Imposes, parce que les tests doivent pouvoir s'authentifier : ils interrogent
# l'API d'administration, et un mot de passe que l'apprenant choisirait seul
# leur serait inconnu. Generes, parce qu'aucun secret ne doit vivre dans le
# depot : celui-ci nait sur la machine, au moment du `run`.
#
# Le fichier est en 0640 pour `student`, le compte humain : l'apprenant le lit,
# et les tests aussi, par le compte de service.
ADMIN_UTILISATEUR=admin-formation
# `openssl rand`, et SURTOUT PAS `tr -dc < /dev/urandom | head -c 24`.
#
# Mesure le 2026-10-16, et le script est mort dessus : sous `set -o pipefail`,
# ce pipeline rend un code NON NUL. `head` prend ses 24 octets puis ferme le
# tube, `tr` recoit SIGPIPE, et `pipefail` retient ce code-la. L'affectation
# reussit, la variable est bien remplie, et `set -e` tue le script juste apres.
#
# L'echec est d'autant plus trompeur que la trace montre la variable affectee :
# on cherche la cause dans la commande SUIVANTE, qui n'a jamais tourne.
#
# `openssl rand -hex 12` rend 24 caracteres sans aucun tube, et openssl est
# installe par la couche machine du socle.
ADMIN_MOTDEPASSE=$(openssl rand -hex 12)

cat > "$TRAVAIL/identifiants.txt" <<IDS
# Genere par le setup du lab, sur cette machine. Ne se trouve pas dans le depot.
#
# L'administrateur NOMINATIF que vous devez creer dans le realm « formation ».
# Les tests s'authentifient avec ces valeurs : les changer les ferait echouer.
ADMIN_UTILISATEUR=$ADMIN_UTILISATEUR
ADMIN_MOTDEPASSE=$ADMIN_MOTDEPASSE
IDS
chown student:docker "$TRAVAIL/identifiants.txt"
chmod 0640 "$TRAVAIL/identifiants.txt"

# Le point de depart que l'apprenant trouve : un repertoire vide, et un fichier
# qui dit ou travailler. Pas de squelette de compose : l'ecrire est le sujet.
cat > "$TRAVAIL/LISEZ-MOI.txt" <<'TXT'
Repertoire de travail du lab iam-02-keycloak-installer.

C'est ici que votre fichier Compose est attendu, sous le nom compose.yaml.
Rien d'autre n'est impose : ni le nom des services, ni celui des volumes.

identifiants.txt porte le nom et le mot de passe de l'administrateur nominatif
que vous devez creer. Les tests s'authentifient avec : ne les changez pas.

Les tests interrogent le serveur, pas vos fichiers.
TXT
chown student:docker "$TRAVAIL/LISEZ-MOI.txt"

# Ce que les tests verifieront d'abord : que rien ne repond. Si quelque chose
# repond ici, la situation n'est pas celle qu'on croit, et il vaut mieux le
# dire tout de suite que laisser le lab se noter sur un etat herite.
for port in 8080 9000; do
  if timeout 2 bash -c "exec 3<>/dev/tcp/127.0.0.1/$port" 2>/dev/null; then
    echo "Le port $port repond deja alors que le lab commence : un service herite n'a pas ete retire." >&2
    ss -ltnp | grep ":$port" >&2 || true
    exit 1
  fi
done

echo "Situation posee : $TRAVAIL est vide, et rien n'ecoute sur 8080 ni 9000."
