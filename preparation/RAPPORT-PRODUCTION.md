# Rapport de production du catalogue IAM

Écrit pour Stéphane, au terme de la production des seize labs demandés par
`preparation/BRIEF-AGENT.md`.

Tout ce qui est chiffré ici a été **mesuré sur la VM `idp.lab`**, et non estimé.
Quand une valeur est une estimation, c'est écrit.

---

## 1. Ce qui est livré

**Seize labs, dont deux épreuves. Les seize ont été joués dans les deux sens le
2026-10-16, chacun en partant d'une situation propre.** La dernière passe a
rejoué le catalogue entier d'un bloc, après les deux correctifs transversaux
décrits en section 5, parce qu'un lab validé avant un correctif n'est pas un lab
validé.

Lecture du tableau : « rouge » est le nombre de tests qui échouent **sans** la
solution, « vert » celui qui passent **avec**, et la durée est celle du cycle
machine complet (`run`, tests sans solution, solution, tests, `clean`).

| Lab | Verdict | Rouge | Vert | Cycle |
|---|---|---|---|---|
| `iam-02-keycloak-installer` | VALIDE le 2026-10-16 | 6 | 6 | 1 min 25 s |
| `iam-04-client-oidc-pkce` | VALIDE le 2026-10-16 | 7 | 7 | 1 min 05 s |
| `iam-05-api-protegee` | VALIDE le 2026-10-16 | 6 (+1 vert) | 7 | 0 min 39 s |
| `iam-01-annuaire-lldap` | VALIDE le 2026-10-16 | 8 (+1 vert) | 9 | 0 min 47 s |
| `iam-03-federation-ldap` | VALIDE le 2026-10-16 | 6 | 6 | 0 min 55 s |
| `iam-06-federation-saml` | VALIDE le 2026-10-16 | 7 | 7 | 0 min 45 s |
| `iam-11-federation-externe` | VALIDE le 2026-10-16 | 7 | 7 | 0 min 50 s |
| `iam-12-depanner-integration` | VALIDE le 2026-10-16 | 3 (+3 verts) | 6 | 0 min 35 s |
| `iam-epreuve-n1` | VALIDE le 2026-10-16 | 10 | 10 | 1 min 48 s |
| `iam-07-mfa-keycloak` | VALIDE le 2026-10-16 | 6 (+1 vert) | 7 | 1 min 47 s |
| `iam-08-depart-collaborateur` | VALIDE le 2026-10-16 | 6 (+1 vert) | 7 | 1 min 00 s |
| `iam-13-revue-des-acces` | VALIDE le 2026-10-16 | 6 | 6 | 0 min 53 s |
| `iam-14-plateforme` | VALIDE le 2026-10-16 | 8 | 8 | 1 min 52 s |
| `iam-09-sauvegarde-montee-version` | VALIDE le 2026-10-16 | 8 | 8 | 2 min 09 s |
| `iam-10-realm-as-code` | VALIDE le 2026-10-16 | 7 | 7 | 0 min 51 s |
| `iam-epreuve` | VALIDE le 2026-10-16 | 16 | 16 | 2 min 16 s |

**Distros jouées : `ubuntu24` seule.** Tous les labs déclarent `ubuntu24`, et
c'est la seule cible provisionnée. La VM de référence tourne sur AlmaLinux 10
côté hôte, mais ce n'est pas la distro du lab : c'est l'hôte KVM.

Les seize solutions sont **chiffrées avec ansible-vault**. `.vault-pass` est
généré sur ta machine, gitignoré, et n'a jamais été affiché : il est à la racine
du dépôt.

---

## 2. La table de branchement

| id | Titre exact (FR) | `doc_url` | Env | Durée visée |
|---|---|---|---|---|
| `iam-01-annuaire-lldap` | Organiser des comptes et des groupes dans un annuaire | `/docs/services/identite/lldap/` | vm | 30m |
| `iam-02-keycloak-installer` | Installer Keycloak avec sa base de données | `/docs/services/identite/keycloak/installation/` | vm | 40m |
| `iam-03-federation-ldap` | Fédérer un annuaire dans le fournisseur | `/docs/services/identite/keycloak/federation-ldap/` | vm | 40m |
| `iam-04-client-oidc-pkce` | Connecter une application en OIDC avec PKCE | `/docs/services/identite/keycloak/securiser-application-oidc/` | vm | 45m |
| `iam-05-api-protegee` | Protéger une API par jetons d'accès | `/docs/services/identite/keycloak/proteger-une-api/` | vm | 50m |
| `iam-06-federation-saml` | Fédérer une application en SAML | `/docs/services/identite/fondamentaux/saml/` | vm | 50m |
| `iam-07-mfa-keycloak` | Exiger un second facteur, de certains seulement | `/docs/services/identite/keycloak/mfa-flows/` | vm | 45m |
| `iam-08-depart-collaborateur` | Couper les accès de quelqu'un qui part | `/docs/services/identite/keycloak/revue-des-acces/` | vm | 40m |
| `iam-09-sauvegarde-montee-version` | Sauvegarder ce qui doit l'être, monter de version, et prouver que rien n'est perdu | `/docs/services/identite/keycloak/production/` | vm | 60m |
| `iam-10-realm-as-code` | Décrire un realm en code, l'appliquer, et rattraper la dérive | `/docs/services/identite/keycloak/configuration-as-code/` | vm | 50m |
| `iam-11-federation-externe` | Déléguer la connexion à un fournisseur externe | `/docs/services/identite/keycloak/federation-entrante/` | vm | 40m |
| `iam-12-depanner-integration` | Réparer une intégration qui ne marche plus | `/docs/services/identite/keycloak/depanner-integration/` | vm | 40m |
| `iam-13-revue-des-acces` | Automatiser le cycle de vie, et conduire une vraie revue | `/docs/services/identite/keycloak/revue-des-acces/` | vm | 45m |
| `iam-14-plateforme` | Faire authentifier un cluster et un outil par le fournisseur | `/docs/services/identite/keycloak/plateforme/` | vm | 60m |
| `iam-epreuve-n1` | Épreuve de niveau 1 : monter un fournisseur, fédérer, brancher une application et une API | `/docs/services/identite/epreuve-niveau-1/` | vm | 90m |
| `iam-epreuve` | Épreuve finale : une identité de bout en bout | `/docs/services/identite/epreuve-niveau-2/` | vm | 120m |

**Les `doc_url` sont celles des fiches, et les leçons correspondantes n'existent
pas encore toutes.** Le contrôle réseau de `validate-structure --check-urls`
n'a donc pas été joué : il échouerait sur les leçons à écrire, ce qui est une
information sur le site et non sur les labs.

**Deux labs partagent une `doc_url` :** `iam-08` et `iam-13` pointent tous deux
sur `revue-des-acces`. Ils traitent deux sujets distincts (couper les accès de
quelqu'un qui part, et automatiser le cycle de vie plus conduire la revue), et
ils mériteront deux leçons. C'est à trancher au moment du branchement.

**Sur la durée visée.** `estimated_time` est une **estimation calibrée sur le
volume de travail**, et non une mesure : les durées mesurées sont celles du
cycle machine, où une solution Ansible fait en une minute ce qu'une personne
fait en quarante. Les mesurer pour de vrai demande de faire jouer les labs par
des gens, et c'est la seule case de ce rapport qui reste à remplir par
l'observation.

---

## 3. Divergences avec les fiches, et pourquoi

Chaque fois, la réalité du logiciel a tranché, et c'est elle qui a gagné.

**`iam-01`** : la fiche demandait de créer l'arborescence. **LLDAP impose son
arbre** (`ou=people`, `ou=groups`) et ne permet pas d'en créer d'autre. Le lab
porte donc sur ce que l'annuaire permet réellement, et les appartenances
passent par son API : un `member:` dans un LDIF de groupe est accepté puis
ignoré, et un `ldapmodify add: member` est refusé.

**`iam-06`** : le cas d'échec « horloges désynchronisées » est **abandonné**. Il
demande deux machines dont les horloges divergent, et la topologie n'en fournit
qu'une. Le reste des cas d'échec de la fiche est couvert.

**`iam-07`** : la fiche parlait d'une condition de groupe. **Keycloak n'a pas de
condition de groupe** : il a une condition de rôle. Le lab attache donc un rôle
au groupe, ce qui fait suivre l'exigence à l'appartenance et répond à
l'intention de la fiche.

**`iam-08`** : la fiche demandait de désactiver le compte à la source.
**LLDAP ne le permet pas.** Le lab retire les appartenances à la source et
désactive côté fournisseur, ce qui est le geste réel dans cette topologie.

**`iam-09`** : la fiche ne mentionne ni TLS ni reverse proxy. Un commentaire que
j'avais écrit dans `shared/compose-socle.yaml` attribuait pourtant le TLS à ce
lab : c'était faux, et c'est corrigé. Le lab porte sur la sauvegarde et la
montée de version, sur une instance **dédiée** (ports 8081 et 9001) : une base
migrée ne redescend pas, et monter le socle laisserait les quinze autres labs
dans un état qu'ils n'ont pas demandé.

**`iam-10`** : la fiche laissait le choix entre le provider Terraform et
keycloak-config-cli. **La mesure a tranché** : le dernier tag stable de
`adorsys/keycloak-config-cli` est 6.5.1 pour Keycloak **24** (mai 2026), et
rien au-delà hormis `edge`. Le provider est en 5.10.0 du 2026-10-05 et vit sous
l'organisation `keycloak` sur GitHub. On n'enseigne pas avec un outil dont la
version supportée s'arrête deux majeures en arrière.

**`iam-14`** : la fiche demandait k3d ou kind. **k3d**, et le TLS devant l'IdP
est posé par le **setup**, pas par l'apprenant : un apiserver Kubernetes refuse
un issuer en http, le lab serait injouable sans TLS, et ce n'est pas son sujet.
L'outil de plateforme est **Grafana**, choisi parce qu'il parle OIDC générique,
pèse 150 Mo, et porte un piège réel (sans `use_pkce`, l'erreur part au callback
et se déguise en retour sur la page de connexion).

**Les deux épreuves** n'incluent pas le socle IAM : installer le fournisseur est
leur première question. Elles **retirent** le socle qu'un autre lab aurait
laissé, volumes compris, parce qu'il occupe exactement leurs ports. Vérifié
qu'un lab ordinaire se rejoue ensuite sans rien faire de particulier.

---

## 4. Les faits mesurés, et ce qu'ils ont infirmé

Une sélection de ceux qui ont changé la conception d'un lab. Tous sont datés et
écrits dans les en-têtes des tests et des solutions concernés.

**Ce qui a été vérifié, et qui tient :**

- `ready_tcp` seul ne prouve rien sur un port publié : le proxy de Docker
  accepte les connexions avant que le service écoute ;
- depuis le conteneur de Keycloak, `127.0.0.1:3890` est **fermé** : avec
  `ldap://127.0.0.1:3890`, la fédération se déclare, s'active, et la
  synchronisation rend « 0 imported users » en HTTP 200, sans aucune erreur ;
- `scimApiEnabled` se pose **à la racine** de la représentation du realm : dans
  ses `attributes`, le PUT rend 204 et la valeur relue reste fausse ;
- l'API SCIM attend pour audience **sa propre URL** ; trois candidats
  plausibles ont été essayés avant ;
- l'API des workflows rend du **YAML**, même vide (`--- []`), et `jq` la refuse
  avec « Invalid numeric literal » dans les deux cas ;
- en Kubernetes 1.37, les drapeaux `--oidc-*` **n'existent plus** : seule la
  configuration structurée, qui **refuse** un issuer en http et le dit
  (« URL scheme must be https ») en ne démarrant pas ;
- `kubectl --token` est **ignoré** quand le kubeconfig courant porte un
  certificat client : `auth whoami` répond alors `system:admin` ;
- `kc.sh export` dans le conteneur en marche sort en **1** et écrit quand même
  les fichiers ; `<realm>-realm.json` ne contient **aucun compte**, et aucun
  fichier d'export ne contient d'événement ;
- le secret d'un client confidentiel est **en clair dans `terraform.tfstate`**,
  créé en 644, et son `.backup` est **recréé en 644 à chaque application** ;
- `conditional-user-configured` laisse entrer un compte **sans** second facteur
  même avec l'étape OTP en REQUIRED ;
- désactiver un compte **ne ferme pas** ses sessions, et retirer une
  appartenance fédérée est refusé par le fournisseur en lecture seule, puis
  exige un vidage du cache des comptes fédérés que rien n'indique.

**Ce qui a été infirmé :**

- une fiche supposait qu'on pouvait créer son arborescence dans LLDAP : non ;
- une fiche supposait une condition de groupe dans Keycloak : il n'y en a pas ;
- une fiche supposait une désactivation côté source : LLDAP ne la propose pas ;
- `keycloak-config-cli` paraissait le choix naturel pour la configuration en
  code : sa dernière version stable s'arrête à Keycloak 24.

---

## 5. Deux correctifs transversaux, nés d'un défaut trouvé en jouant

**Le jeton d'administration était journalisé dans dix `prepare.sh`.** Le
`set -x` traçait la ligne `if [ -z "$JETON" ]`, et ce journal est celui que
`dsoxlab support` collecte et qu'un apprenant joint à une demande d'aide. Le
jeton vit soixante secondes, ce qui limite les dégâts sans rien excuser. Les
quatorze labs sont indemnes, et un contrôle le vérifie.

**`commande | head -1` sous `set -o pipefail`** : `head` ferme le tuyau,
l'amont meurt sur SIGPIPE, le pipeline rend 141 et `set -e` tue le script. Le
défaut est d'autant plus vicieux qu'il dépend de la taille du tampon : la même
commande passe parfois. Retiré de `iam-05`, `iam-10` et `iam-14`, tous rejoués.

---

## 6. Ce qui reste

**Ce qui est de la dette, et que je signale plutôt que de la masquer :**

1. **Cinq labs ne sont pas entièrement rouges avant le travail.** `iam-12` est
   le plus net : trois tests sur six passent dès le départ. `iam-01`, `iam-05`,
   `iam-07` et `iam-08` en ont un chacun. Ce sont des contrôles qui lisent un
   état sain que le setup fournit déjà, ou une absence de dégât. Les labs
   produits après ce constat (`iam-09`, `iam-10`, les deux épreuves) exigent la
   tâche avant de conclure, et c'est le motif à reprendre sur ces cinq.

2. **Les indices sont en ASCII sans accents**, dans les quatorze labs qui en
   ont. C'est une convention que j'ai prise au premier lab et tenue pour la
   cohérence du catalogue. Elle contredit la règle du dépôt sur les diacritiques
   et mérite d'être tranchée dans un sens ou dans l'autre, d'un seul geste.

3. **Le chronométrage des épreuves n'est tenu par aucun test.** `dsoxlab` ne
   chronomètre pas. Le setup consigne `DEBUT_EPREUVE` dans le fichier
   d'identifiants et l'énoncé annonce la durée visée, mais rien ne la mesure :
   un test qui échouerait sur une pause-café ne mesurerait pas la compétence.

4. **Les durées apprenantes restent des estimations** (section 2).

5. **`--check-urls` n'a pas été joué**, les leçons n'existant pas toutes.

**Hors de ce catalogue, et relevé en passant :**

- `kubernetes-dsoxlab-training` porte un vestige mort de `_find_lab_root`, hérité
  du conftest avant son correctif ;
- le catalogue `cloud` a un commit local non poussé ;
- `containers-dsoxlab-training` existe sur GitHub, en privé, et n'est pas cloné
  localement : il échappe à tout relevé.

**Rien n'est poussé.** Les vingt-deux commits du dépôt sont locaux, sur `main`
de `iam-dsoxlab-training`, dont vingt-et-un datés du 2026-10-16, et la
livraison t'appartient.
