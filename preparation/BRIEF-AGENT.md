# Brief : construire le catalogue de labs `iam-dsoxlab-training`

Tu reprends ce chantier **sans contexte** : tout ce qu'il faut est dans ce
dossier `preparation/`. Lis ce brief en entier, puis le cadrage et les fiches,
avant d'écrire une ligne.

Écrit le 2026-10-15, à la fin de la session qui a créé la formation IAM du
site. Décision de Stéphane du même jour : les labs ont été reportés pendant la
création de la formation, puis il a demandé ce dossier pour qu'un agent les
construise dans une autre session.

## 1. Mission

Créer, dans `~/Projets/iam-dsoxlab-training/` (ce dossier, dont `preparation/`
est le seul contenu au départ), le **catalogue DSOXLab** de la formation
« Gestion des identités et des accès (IAM) » du site
`www.stephane-robert.info` : **14 labs et 2 épreuves**, décrits un par un
dans `fiches/`.

**Fini veut dire**, pour chaque lab :

1. il respecte le **contrat DSOXLab** (`modele/lab.schema.json`,
   `modele/meta.schema.json`) et la structure du modèle `modele/lab-linux/` ;
2. il a été **joué en entier sur une VM, dans les deux sens** : après
   `dsoxlab run`, `dsoxlab check` rend **0** (le travail n'est pas fait) ;
   après la solution de référence, il rend **100** ; `dsoxlab clean` ne laisse
   rien. Chaque cas d'échec de sa fiche fait aussi échouer un test ;
3. il porte un **verdict daté** dans `validation-labs.json` ;
4. sa **durée** est **mesurée** en le jouant, pas estimée ;
5. il est **commité en local** (jamais de push : la livraison est un geste de
   Stéphane).

Ne déclare jamais « VALIDE » un lab que tu n'as pas joué. Un lab non fini se
dit non fini.

## 2. Ce que contient `preparation/`

| Fichier | Rôle |
|---|---|
| `BRIEF-AGENT.md` | ce brief |
| `cadrage-formation-iam.md` | plan de la formation, compétences, décisions D1 à D9 (copie du `todo/formation-iam-cadrage.md` du site) |
| `README-labs-iam-site.md` | socle technique, règles du site, liste des labs (copie de `todo/labs-iam/README.md` du site) |
| `fiches/*.md` | **une fiche par lab** : objectif, gestes, **état vérifié par les tests**, cas d'échec, indices, points à vérifier avant d'écrire. C'est ton cahier des charges. |
| `modele/lab-vm-kubernetes/` | **modèle de STRUCTURE** : un lab complet du catalogue Kubernetes en `runtime.type: vm` (`lab.yaml` avec `targets`, `setup.yaml` et `cleanup.yaml` Ansible, `fixtures/`, `challenge/` avec `hints.yaml` et `tests/` pytest). C'est la forme des labs IAM, qui tournent sur VM. |
| `modele/lab-linux/` | un lab du catalogue Linux (runtime `shell`) : modèle des **conventions de rédaction** et des tests, pas de la structure VM |
| `modele/meta-kubernetes.yml`, `modele/meta-devsecops.yml` | deux `meta.yml` commentés, provider KVM |
| `modele/CLAUDE-catalogue-linux.md`, `modele/CLAUDE-catalogue-kubernetes.md` | les règles internes des deux catalogues : **à lire en entier**, ce sont les leçons de plusieurs centaines de labs (validation dans les deux sens, solutions, chiffres publiés, pièges) |
| `modele/lab.schema.json`, `meta.schema.json` | le contrat dsoxlab (copie de `~/Projets/dsoxlab/schemas/`, à **revérifier** contre la version courante de dsoxlab) |
| `scripts-executes/` | scripts **réellement exécutés** le 2026-10-15 contre Keycloak 26.7.0 par les auteurs des leçons : la base de plusieurs labs (§6) |

Les dépôts de référence sont lisibles en entier sur le poste :
`~/Projets/linux-dsoxlab-training` (modèle principal, avec `scripts/` dont le
validateur et `validation-labs.json`), `~/Projets/devsecops-dsoxlab-training`
et `~/Projets/kubernetes-dsoxlab-training` (labs sur VM et cluster),
`~/Projets/dsoxlab` (la CLI et ses schémas).

## 3. Règles non négociables

- **DSOXLab : toujours la dernière version** de la CLI avant de commencer
  (`dsoxlab --version`, mise à jour si besoin). Les commandes `dsoxlab` sont
  autorisées ; seul `destroy` demande confirmation à Stéphane.
- **Provider `kvm`**, distros **`alma10`** et **`ubuntu24`** seulement
  (`debian12` est annoncé mais cassé). `runtime.type: vm`, jamais `kvm` ni
  `incus`. Méthode et pièges : skill `lab-vm-validation` du dépôt du site
  (`~/Projets/test-astro-5/.claude/skills/lab-vm-validation/SKILL.md`). Tout
  nouvel hôte s'ajoute **en fin** de `infra.hosts` (les IP dérivent de la
  position).
- **Validation sur l'état, jamais sur les commandes tapées** : les tests
  interrogent Keycloak (API d'administration, endpoints OIDC), l'annuaire
  (`ldapsearch`) et les applications témoins.
- **Épinglage** : toute image `image:tag@sha256:<digest>` relevé sur le
  registre au moment d'écrire, jamais `:latest` ; toute action GitHub par SHA
  de commit. Dépendances Python ou Node des témoins épinglées.
- **Aucun secret en dur** dans le dépôt : mots de passe et secrets de client
  **générés** par le setup (les scripts de `scripts-executes/` utilisent
  `admin/admin` et un mot de passe de test : acceptable pour un essai jetable,
  pas pour un lab publié).
- **Solutions chiffrées** (décision de Stéphane du 2026-10-15, convention du
  catalogue Linux, pas celle du catalogue Kubernetes) : une solution par lab,
  `solution.yaml` (playbook) sous `solution/<lab>/`, chiffrée avec
  `ansible-vault` ; le mot de passe `.vault-pass` à la racine est **généré par
  toi**, **gitignoré**, jamais commité ni affiché ; reprends le test qui refuse
  une solution en clair (`tests/test_solutions_chiffrees.py` du catalogue
  Linux). Dis à Stéphane dans ton rapport **où** est `.vault-pass` (pas sa
  valeur). Aucun `challenge/solution.sh` en clair.
- **Validateur** : reprends `scripts/valider-labs.py` du catalogue Linux (ou
  celui du catalogue Kubernetes, plus proche du runtime VM ; compare les deux),
  avec `isolation_vm.py` : un appel par lab, verdict dans
  `validation-labs.json`. Ne réimplémente pas la logique : enchaîne les
  commandes dsoxlab comme eux.
- **Titre identique** entre `lab.fr.yaml` et le futur bloc `<Lab>` de la
  leçon ; **`doc_url`** = la leçon qui hébergera le bloc (§5).
- **Commits en local uniquement**, jamais de push, jamais de `--no-verify`.
- **Ton espace de travail temporaire** : un sous-dossier à toi dans le
  scratchpad de ta session, jamais à la racine.
- **Réponds et écris en français** (catalogue bilingue FR/EN comme le modèle).

## 4. Ordre de travail

1. Lire les deux `CLAUDE-catalogue-*.md`, puis les deux dépôts eux-mêmes
   (`~/Projets/kubernetes-dsoxlab-training` pour la structure VM et
   `setup.yaml`, `~/Projets/linux-dsoxlab-training` pour les solutions
   chiffrées, `scripts/valider-labs.py`, `scripts/verify-solutions.py` et le
   format de `validation-labs.json`).
2. Créer le squelette du dépôt : `meta.yml` (`repo.id: iam-dsoxlab-training`,
   `category` à confirmer contre le schéma, `blog_url:
   https://www.stephane-robert.info/docs/services/identite/`, provider
   `kvm`), README FR/EN, licence et fichiers communs repris du modèle.
3. Construire le **socle** partagé : Compose Keycloak + PostgreSQL + LLDAP,
   **application témoin** (connexion OIDC) et **API témoin** (jetons d'accès),
   versionnées dans le dépôt. Rejouer `scripts-executes/` pour te caler.
4. Écrire et **jouer** les labs dans l'**ordre du parcours** (table du §5),
   un par un : fiche → lab → jeu complet → verdict → commit.
5. Les **deux épreuves** en dernier : sans `hints.yaml`, chronométrées,
   barème fixé **après** les avoir jouées.

## 4 bis. Topologie proposée (à confirmer en jouant le premier lab)

- **Une VM** `idp.lab` (`ubuntu24`, puis rejeu sur `alma10` si le temps le
  permet), 2 vCPU et **4 Go** au moins : Keycloak, PostgreSQL, LLDAP, les
  témoins et, pour le lab `iam-11`, un **second Keycloak** qui joue
  l'entreprise partenaire, tous en Docker Compose. Docker y est installé par
  le `setup.yaml` commun.
- Lab `iam-14` (Kubernetes) : un cluster **k3d ou kind dans la VM** (règle du
  site : exemples Kubernetes sur k3d ; avec kind, rester **sous 0.32**, la
  0.32 a cassé `v1beta3`). Pas de cluster sur le poste.
- Lab `iam-06` (SAML) : un fournisseur de service témoin à **choisir**
  (maintenu, image épinglable) ; justifie le choix dans le rapport.
- Ne teste jamais un service dans un conteneur à la place d'une VM quand le
  lab parle de systemd ou de l'hôte ; ici tout est conteneurisé **sur** la VM,
  ce qui est conforme.

## 4 ter. Si tu bloques

- Une fonction manque à dsoxlab, ou le schéma refuse un champ dont tu as
  besoin : **ne contourne pas** et ne modifie pas dsoxlab. Note le besoin
  précis dans ton rapport ; une issue sur `stephrobert/dsoxlab` se propose,
  elle ne se crée que sur accord de Stéphane.
- Un geste refusé par les permissions ou par le garde-fou (destruction,
  `--force`, suppression) : arrête-toi et demande, ne le refais pas autrement.
- Un fait de la fiche se révèle faux en jouant le lab : la réalité gagne,
  corrige le lab et signale l'écart (la leçon du site sera corrigée ensuite).

## 5. Labs, leçons d'accueil et ordre

Ordre de jeu = ordre du parcours de la formation (pas la numérotation des
fiches). Les leçons existent sur la branche `feat/formation-iam` du dépôt du
site (worktree `~/Projets/test-astro-5/.claude/worktrees/formation-iam`),
**pas encore fusionnée dans main** à la date de ce brief : vérifie leur URL
publiée avant de figer les `doc_url`. Racine des URL :
`https://www.stephane-robert.info/docs/services/identite/`.

| Ordre | Fiche | Leçon d'accueil (`doc_url`, sous la racine) | Statut de la leçon au 2026-10-15 |
|---|---|---|---|
| 1 | `iam-02-keycloak-installer` | `keycloak/installation/` | publiée |
| 2 | `iam-04-client-oidc-pkce` | `keycloak/securiser-application-oidc/` | publiée |
| 3 | `iam-05-api-protegee` | `keycloak/proteger-une-api/` | écrite, en relecture |
| 4 | `iam-01-annuaire-lldap` | `lldap/` | publiée |
| 5 | `iam-03-federation-ldap` | `keycloak/federation-ldap/` | publiée |
| 6 | `iam-06-federation-saml` | `fondamentaux/saml/` | publiée |
| 7 | `iam-11-federation-externe` | « Fédération entrante » | **à écrire** |
| 8 | `iam-12-depanner-integration` | « Dépanner une intégration OIDC et SAML » | **à écrire** |
| E1 | `iam-epreuve-n1` | épreuve du niveau 1 | **à écrire** |
| 9 | `iam-07-mfa-keycloak` | « MFA, passkeys et flows dans Keycloak » | **à écrire** |
| 10 | `iam-08-depart-collaborateur` | « Revue des accès et automatisation » | **à écrire** |
| 11 | `iam-13-revue-des-acces` | idem | **à écrire** |
| 12 | `iam-14-plateforme` | « Kubernetes, Vault et les outils » | **à écrire** |
| 13 | `iam-09-sauvegarde-montee-version` | « Keycloak en production » | **à écrire** |
| 14 | `iam-10-realm-as-code` | « Configuration en tant que code » | **à écrire** |
| E2 | `iam-epreuve` | `fondamentaux/capstone/` (brouillon à réécrire) | brouillon |

Une leçon « à écrire » n'empêche pas de construire son lab : la fiche suffit.
Laisse alors un `doc_url` provisoire et liste-le dans ton rapport.

## 6. Faits déjà vérifiés à la source (2026-10-15)

- **Keycloak** : dernière version **26.8.1** (2026-10-13) ; les leçons du site
  ont été jouées en **26.7.0**. **26.8.0** passe l'**API SCIM** native en
  « supported » (Keycloak **serveur** SCIM, base `/realms/<realm>/scim/v2`,
  activée par realm) ; **26.6** passe les **Workflows** (gouvernance, YAML) en
  « supported » ; passkeys natives « supported » depuis 26.4. Défauts d'un
  realm créé : `accessTokenLifespan` 300 s (60 s pour `master`),
  `ssoSessionIdleTimeout` 1800, `ssoSessionMaxLifespan` 36000,
  `revokeRefreshToken` false. **Bearer-only** est un type de client
  déprécié. Pas de « Refresh Token Lifespan » : le refresh est borné par SSO
  Session Idle/Max. Port de gestion **9000** (santé, métriques).
- **authentik** : dernière **2026.8.4** ; leçons jouées en **2026.2.1** ;
  prérequis officiels **2 cœurs, 2 Go de RAM** ; le socket Docker du worker
  sert aux outposts (risque documenté, proxy de socket recommandé).
- **LLDAP** : **0.6.3** ; ce n'est **pas** un fournisseur OIDC (l'OIDC vient
  d'un IdP placé devant) ; ports vus en lab : 3890 (LDAP), 6360 (LDAPS),
  17170 (web).
- **Normes** : RFC 9700 (BCP OAuth, janvier 2025), OAuth 2.1 toujours
  brouillon, RFC 10017 (applications navigateur, BFF), NIST SP 800-63B-4
  (15 caractères seul, aucune règle de composition, passkeys synchronisées
  interdites en AAL3).

## 7. Ce que montrent les scripts de `scripts-executes/`

- `jetons-sessions/` (Keycloak 26.7.0, `start-dev`, realm de test) :
  `setup.sh` et `lab1.sh` préparent Keycloak ; `lab2.sh`, `lab3.sh` et
  `obs1-3.sh` obtiennent, décodent, rafraîchissent (sans puis avec rotation :
  `invalid_grant` « Maximum allowed refresh token reuse exceeded »),
  introspectent, déconnectent (`204`, puis session inactive mais access token
  encore valide jusqu'à `exp`), révoquent et ferment les sessions. Sortie
  complète dans `lab3.out`. Base de la fiche `iam-08-depart-collaborateur`
  (révocation, fermeture des sessions) et des tests qui valident un jeton.
- `cryptographie-jetons/page.sh` : les commandes `openssl` de la leçon de
  cryptographie (signature, vérification, falsification, chaîne X.509).
  Utile pour l'épreuve et les tests de validation de jetons.
- `proteger-une-api/` (Keycloak 26.7.0, Python 3.12) : **l'API témoin**
  (`api.py`, PyJWT 2.15.1 et cryptography 50.0.2 épinglés dans
  `requirements.txt`, port 8090) et les blocs de la leçon dans l'ordre
  (`blocs/01` à `10`). Sorties de deux rejeux complets dans `out.txt` (avec
  l'expiration à 300 s) et `out2.txt`. Constaté : sans jeton 401
  `WWW-Authenticate: Bearer` ; mauvaise audience 401 `invalid_token` ;
  lecture 200 ; écriture avec lecture seule 403 `insufficient_scope` ;
  client credentials `sauvegarde` 200 en lecture et 403 en écriture ;
  introspection ; device grant (`device.sh` approuve par curl, l'approbation
  n'est pas dans la leçon) ; token exchange V2. Base directe de la fiche
  `iam-05-api-protegee` et de l'épreuve de niveau 1. Écart connu : altérer la
  signature par ROT13 donne parfois « Invalid crypto padding » au lieu de
  « Signature verification failed » ; pour un test de lab, remplace plutôt la
  signature entière.

Les chemins internes à ces scripts pointent vers le scratchpad d'une session
disparue : adapte-les, ne les exécute pas tels quels.

## 8. Ce qui n'est PAS ta mission

- **Câbler les labs dans les leçons** (bloc `<Lab>` dans une section
  `## Mettre en pratique`) : cela se fait dans le dépôt du site, dans un
  worktree, après validation des labs. Livre à la place, dans ton rapport, la
  table `id | titre exact | doc_url | env | durée mesurée` pour chaque lab
  validé.
- Écrire ou modifier les leçons du site.
- Pousser quoi que ce soit, publier, créer le dépôt GitHub.

## 9. Rapport attendu à la fin

Par lab : statut (validé / partiel / non fait), verdict et date, durée
mesurée, distros jouées, écarts avec la fiche et pourquoi, faits vérifiés ou
infirmés au passage (versions, libellés). Puis la table de câblage du §8, et
la liste de ce qui reste.
