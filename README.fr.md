# Formation IAM : brancher une application sur un fournisseur d'identité, puis l'exploiter

**Langue :** [English](./README.md) · [Français](./README.fr.md)

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](./LICENSE)

Les labs vérifiables de la
[formation gestion des identités et des accès](https://blog.stephane-robert.info/docs/services/identite/)
du blog, joués avec [dsoxlab](https://github.com/stephrobert/dsoxlab).

## Ce que c'est

**Seize labs, un fournisseur d'identité, et la suite de tests la plus dense de
toute la collection.** Une formation IAM peut s'enseigner entièrement sur le
papier : schémas de flux, noms de protocoles, captures d'une console
d'administration. L'apprenant en sort en reconnaissant le vocabulaire, sans
avoir jamais vu un jeton refusé pour la bonne raison.

Or rien ne se prouve par la lecture dans ce domaine. Un client OIDC mal
configuré rend un jeton qui ressemble à un jeton valide. Une API qui ne
vérifie pas l'audience accepte un jeton émis pour quelqu'un d'autre. Une
déconnexion qui ferme la session laisse l'ancien jeton d'accès valide jusqu'à
son expiration. Ces trois faits se constatent en une commande chacun et ne
s'oublient plus ensuite ; expliqués, ils glissent.

Ce catalogue donne donc à l'apprenant les moyens de **vérifier lui-même**,
contre un vrai fournisseur d'identité, avec de vraies applications.

### La règle qui gouverne tout le reste

**Un lab est noté sur l'état du système, jamais sur les commandes tapées.**

L'apprenant atteint le résultat par le chemin qu'il veut. Les tests
interrogent donc Keycloak par son API d'administration et ses points de
terminaison OIDC, l'annuaire par LDAP, et les applications témoins par leurs
propres réponses.

```python
# NON : on relit ce que l'apprenant a écrit, ce qui ne prouve rien
assert "pkce" in config_lue

# OUI : on demande au fournisseur ce qu'il exige vraiment
client = admin.get(f"/admin/realms/{realm}/clients/{id}")
assert client["attributes"]["pkce.code.challenge.method"] == "S256"
```

## Prérequis

- **Python 3.11+ et [`uv`](https://docs.astral.sh/uv/)**
- **`git`**
- **Un hyperviseur**, puisque tous les labs d'ici sont `runtime: vm` : soit
  **libvirt/KVM** (avec `terraform` et le provider `dmacvicar/libvirt`), soit
  **Incus**. Le provider est déclaré en liste dans [`meta.yml`](./meta.yml), et
  **une liste ne se résout pas d'elle-même** : choisissez-en un avec
  `dsoxlab use --provider kvm`.
- **6 Go de RAM libre et 30 Go de disque** pour la machine unique, `idp.lab`.
  Deux labs sont la raison des 6 Go plutôt que des 4 Go minimum, et la section
  suivante dit lesquels.
- **Un accès réseau sortant** au premier provision, pour récupérer l'image de
  base et les images de conteneurs.

`dsoxlab doctor` dit ce dont ce dépôt a besoin et ce dont il n'a pas besoin, et
distingue un contrôle qui a échoué d'un contrôle qu'il n'a pas pu mesurer.

### La machine, et pourquoi une seule

Une machine virtuelle, déclarée dans `meta.yml` et provisionnée par
`dsoxlab provision` :

| Hôte | Distribution | vCPU | RAM | Disque |
|---|---|---|---|---|
| `idp.lab` | Ubuntu 24.04 | 2 | 6 Go | 30 Go |

Tout y tourne en conteneurs : Keycloak, sa base PostgreSQL, l'annuaire LLDAP,
l'application témoin et l'API témoin. Deux labs demandent davantage :

- `iam-11-federation-externe` démarre un **second Keycloak**, qui joue le
  fournisseur d'identité de l'entreprise partenaire. Un compte chez un
  fournisseur public rendrait le lab injouable hors ligne et dépendant d'un
  service que personne ne maîtrise ;
- `iam-14-plateforme` monte un **cluster k3d dans la machine**, pour brancher
  son serveur d'API sur le fournisseur d'identité.

Rien ne tourne sur le poste de l'apprenant : un fournisseur d'identité qui
écoute sur la machine de travail finit par entrer en collision avec autre
chose, et ce n'est pas ce que le lab enseigne.

## Installation

`dsoxlab` est publié sur [PyPI](https://pypi.org/project/dsoxlab/).
Installez-le en outil autonome, pour qu'il reste hors de ce dépôt :

```bash
# 1. La CLI dsoxlab (outil externe, hors de ce dépôt)
uv tool install dsoxlab

# 2. Ce catalogue de labs
git clone https://github.com/stephrobert/iam-dsoxlab-training.git
cd iam-dsoxlab-training

# 3. Vérifier le contrat et la machine
dsoxlab validate-structure
dsoxlab doctor
```

### Votre premier lab, en cinq minutes

La machine doit exister d'abord : rien ici ne tourne sur votre propre poste.

```bash
export LAB_HOME=$PWD
dsoxlab use --provider kvm           # une liste de providers ne se résout pas seule
dsoxlab provision                    # crée idp.lab, une fois

dsoxlab list-labs                    # les seize labs, dans l'ordre de jeu
dsoxlab run       iam-02-keycloak-installer
dsoxlab challenge iam-02-keycloak-installer
dsoxlab check     iam-02-keycloak-installer

dsoxlab clean     iam-02-keycloak-installer   # défait le lab, garde la machine
dsoxlab destroy                               # rend la machine
```

`provision` sort en code non nul si un hôte ne répond pas, et nomme les
domaines orphelins qu'il a laissés plutôt que d'annoncer un succès. Un `check`
joué sur un lab jamais démarré ne mesure rien, et le dit au lieu d'enregistrer
un 0.

### Garder à jour

```bash
uv tool upgrade dsoxlab        # le moteur, publié sur PyPI
git -C <ce dépôt> pull         # le catalogue
```

Le moteur et le catalogue avancent indépendamment : un nouveau `dsoxlab` ne
demande jamais de recloner les labs, et de nouveaux labs ne demandent jamais de
mettre l'outil à jour, tant que la version du contrat correspond.

## Comment ça marche

### Le contrat déclaratif, à deux niveaux

Ce dépôt **n'est pas la CLI**. Un défaut du moteur se corrige dans
[dsoxlab](https://github.com/stephrobert/dsoxlab), ou s'y signale en issue.
Ici, tout ce qui pilote la CLI est déclaratif :

- **`meta.yml`** à la racine déclare l'identité du dépôt, l'**infrastructure**
  (provider, réseau `lab-iam`, `10.10.80.0/24`, et l'hôte unique `idp.lab`) et
  l'**ordre** des sections affichées par `list-labs` ;
- **`lab.yaml`** par lab déclare ses `skills`, son `level`, son `runtime` (type
  et targets), ses `distros`, son `doc_url` et un bloc `validation`. Un
  `lab.fr.yaml` surcharge `title` et `description` en français, et rien
  d'autre ;
- **`setup.yaml`** et **`cleanup.yaml`** posent et défont l'état de la
  machine ;
- **`challenge/tests/test_functional.py`** porte la preuve.

Les gabarits Terraform et cloud-init sont **packagés dans dsoxlab**, pas ici :
ce dépôt ne déclare que son bloc `infra:` et sa clé publique dans `ssh/`.

### Le cycle de vie d'un lab

```bash
dsoxlab list-labs              # parcourir le catalogue
dsoxlab show      <id>         # métadonnées et état d'un lab
dsoxlab run       <id>         # poser l'état initial et ouvrir la session
dsoxlab challenge <id>         # lire la mission, sans pas-à-pas
dsoxlab hint      <id>         # révéler un indice (déduit du score)
dsoxlab check     <id>         # lancer les tests, calculer et enregistrer le score
dsoxlab clean     <id>         # défaire le lab, garder la machine
dsoxlab progress               # avancement par section, score moyen
```

### Les runtimes

| Runtime | Ce que le lab demande |
|---|---|
| `vm` | la machine `idp.lab`, provisionnée par `dsoxlab provision`, sous Ubuntu 24.04. Keycloak, PostgreSQL, LLDAP et les applications témoins y tournent en conteneurs, démarrés par le `setup.yaml` du lab. |

Les seize labs sont `vm`, et aucun ne déclare `runtime.services` : les
conteneurs appartiennent à la machine, pas au poste de l'apprenant, donc ils y
sont montés par Ansible et non par dsoxlab.

### Le modèle de validation

La validation **prouve l'état, elle ne fait pas confiance à l'apprenant**, et
un lab est prouvé **dans les deux sens** : après `dsoxlab run`, `dsoxlab check`
doit rendre **0**, puisque le travail n'a pas été fait. Après la solution de
référence, il doit rendre **100**. Un test qui passe avant le travail ne mesure
rien, et c'est le défaut le plus coûteux de ce domaine.

Avec 544 assertions pour seize labs, c'est le catalogue le plus dense de la
collection : chaque mécanisme est interrogé là où il vit vraiment, par l'API
d'administration de Keycloak, ses points de terminaison OIDC, LDAP, et les
réponses des applications témoins.

### Les solutions sont chiffrées

L'apprenant doit chercher. Les solutions de référence vivent donc sous
`solution/<lab>/`, chiffrées avec `ansible-vault`, et le mot de passe
(`.vault-pass` à la racine) n'est jamais versionné. Un fichier de solution en
clair est un défaut, que [`tests/test_solutions_chiffrees.py`](./tests/)
refuse.

Le tutoriel d'un lab ne donne pas sa réponse non plus : il enseigne chaque
mécanisme sur un exemple jetable, délibérément nommé hors du sujet du défi, que
l'apprenant doit ensuite transposer.

### Score, indices, avancement

`check` enregistre un score (tests réussis sur total, moins le coût des indices
révélés). Les indices sont **en base64** dans `challenge/hints.yaml`, pour qu'on
n'y accède pas en ouvrant le fichier, et leur coût croît avec leur précision.
L'historique vit dans une base SQLite **locale à ce dépôt**.

Une exécution qui n'a rien mesuré n'est ni une réussite ni un échec : si tous
les tests collectés skippent, `check` n'enregistre aucune note et dit pourquoi.
Un 0 accuserait le lab de ce qui manque au poste, qui est ici le plus souvent
`idp.lab` qui n'est pas debout.

## Catalogue

Deux niveaux, dans l'**ordre de jeu**. Il ne suit pas la numérotation des
fiches : les labs 11 et 12 se jouent au module 4, le 13 au module 6, le 14 au
module 7.

### Niveau 1 : brancher une application sur un fournisseur d'identité

Installer Keycloak avec sa base, brancher une application en OIDC avec PKCE,
protéger une API par jetons d'accès, fédérer un annuaire puis un service SAML,
déléguer la connexion à un fournisseur externe, et diagnostiquer une
intégration cassée. Se termine par l'épreuve de niveau.

| Lab (id) | Titre | Type | Guide compagnon |
|---|---|---|---|
| `iam-02-keycloak-installer` | Installer Keycloak avec sa base de données | lab | [guide](https://blog.stephane-robert.info/docs/services/identite/keycloak/installation/) |
| `iam-04-client-oidc-pkce` | Connecter une application en OIDC avec PKCE | lab | [guide](https://blog.stephane-robert.info/docs/services/identite/keycloak/securiser-application-oidc/) |
| `iam-05-api-protegee` | Protéger une API par jetons d'accès | lab | [guide](https://blog.stephane-robert.info/docs/services/identite/keycloak/proteger-une-api/) |
| `iam-01-annuaire-lldap` | Organiser des comptes et des groupes dans un annuaire | lab | [guide](https://blog.stephane-robert.info/docs/services/identite/lldap/) |
| `iam-03-federation-ldap` | Fédérer un annuaire dans le fournisseur | lab | [guide](https://blog.stephane-robert.info/docs/services/identite/keycloak/federation-ldap/) |
| `iam-06-federation-saml` | Fédérer une application en SAML | lab | [guide](https://blog.stephane-robert.info/docs/services/identite/fondamentaux/saml/) |
| `iam-11-federation-externe` | Déléguer la connexion à un fournisseur externe | lab | [guide](https://blog.stephane-robert.info/docs/services/identite/keycloak/federation-entrante/) |
| `iam-12-depanner-integration` | Réparer une intégration qui ne marche plus | lab | [guide](https://blog.stephane-robert.info/docs/services/identite/keycloak/depanner-integration/) |
| `iam-epreuve-n1` | Épreuve de niveau 1 : monter un fournisseur, fédérer, brancher une application et une API | capstone | [guide](https://blog.stephane-robert.info/docs/services/identite/epreuve-niveau-1/) |

### Niveau 2 : exploiter et gouverner

Exiger une authentification forte, traiter le départ d'un collaborateur, mener
une revue des accès, brancher la plateforme, sauvegarder et monter de version
le fournisseur, et décrire le realm en code. Se termine par l'épreuve finale.

| Lab (id) | Titre | Type | Guide compagnon |
|---|---|---|---|
| `iam-07-mfa-keycloak` | Exiger un second facteur, de certains seulement | lab | [guide](https://blog.stephane-robert.info/docs/services/identite/keycloak/mfa-flows/) |
| `iam-08-depart-collaborateur` | Couper les accès de quelqu'un qui part | lab | [guide](https://blog.stephane-robert.info/docs/services/identite/keycloak/revue-des-acces/) |
| `iam-13-revue-des-acces` | Automatiser le cycle de vie, et conduire une vraie revue | lab | [guide](https://blog.stephane-robert.info/docs/services/identite/keycloak/revue-des-acces/) |
| `iam-14-plateforme` | Faire authentifier un cluster et un outil par le fournisseur | lab | [guide](https://blog.stephane-robert.info/docs/services/identite/keycloak/plateforme/) |
| `iam-09-sauvegarde-montee-version` | Sauvegarder ce qui doit l'être, monter de version, et prouver que rien n'est perdu | lab | [guide](https://blog.stephane-robert.info/docs/services/identite/keycloak/production/) |
| `iam-10-realm-as-code` | Décrire un realm en code, l'appliquer, et rattraper la dérive | lab | [guide](https://blog.stephane-robert.info/docs/services/identite/keycloak/configuration-as-code/) |
| `iam-epreuve` | Épreuve finale : une identité de bout en bout | capstone | [guide](https://blog.stephane-robert.info/docs/services/identite/epreuve-niveau-2/) |

_16 labs. Ce catalogue n'a pas encore de `scripts/gen_catalog.py`, donc ces
tables se tiennent à la main : confrontez-les à `dsoxlab list-labs` quand vous
ajoutez un lab._

## Contribuer

Un lab est prouvé **dans les deux sens** avant d'être fusionné,
`dsoxlab validate-structure` est vert, et l'énoncé existe en anglais et en
français. Un lab entre dans `meta.yml` le jour où il est écrit **et** joué, pas
avant.

Tout ce qui s'affiche est bilingue. Un document traduit d'un seul côté est
signalé par le validateur, et non laissé à la bonne volonté.

## Licence

Voir [`LICENSE`](./LICENSE) (CC BY 4.0).
