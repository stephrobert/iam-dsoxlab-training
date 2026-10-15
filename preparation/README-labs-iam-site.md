# Labs de la formation IAM : dossier de préparation

**Statut : reportés.** Décision de Stéphane du 2026-10-15 : « On peut faire les
labs plus tard. » La formation IAM se construit d'abord sans catalogue
d'exercices ; ce dossier garde tout ce qu'il faut pour l'écrire le jour venu,
sans refaire l'analyse.

Ce qui n'est **pas** reporté : toute leçon qui fait exécuter des commandes est
**rejouée par le lab-validator** sur une VM jetable avant publication (règle B
de `src/content/docs/docs/CLAUDE.md`). Seul le catalogue que l'apprenant joue
avec `dsoxlab` attend.

Plan de la formation : `todo/formation-iam-cadrage.md`.

## Le catalogue à créer

| Champ | Valeur prévue |
|---|---|
| Dépôt | `stephrobert/iam-dsoxlab-training`, cloné dans `~/Projets/iam-dsoxlab-training` (convention des autres catalogues) |
| `repo.id` | `iam-dsoxlab-training` |
| `repo.category` | `iam` (à confirmer contre le schéma `meta.schema.json` de dsoxlab) |
| `blog_url` | `https://blog.stephane-robert.info/docs/services/identite/` |
| Provider | `kvm` (et `incus` si le catalogue le permet) : Keycloak, sa base et l'annuaire tournent sur une VM, pas sur le poste |
| Distros | `alma10` et `ubuntu24` (les seules utilisables, voir la skill `lab-vm-validation`) |

**Modèle à suivre** : `~/Projets/linux-dsoxlab-training` (un lab = un dossier
avec `lab.yaml`, `lab.fr.yaml`, `scenario.md`, `scenario.fr.md`,
`README.md`, `README.fr.md`, `challenge/` avec `hints.yaml` et `tests/`) et
`~/Projets/devsecops-dsoxlab-training` pour un `meta.yml` commenté. Champs d'un
`lab.yaml` relevés le 2026-10-15 : `id`, `title`, `description`, `section`,
`lab_type`, `level`, `bloc`, `difficulty`, `estimated_time`, `runtime`
(`type: vm` pour ce catalogue, jamais `kvm` ni `incus`), `distros`, `skills`,
`doc_url`, `track`, `validation` (`functional`, `security`,
`persistence_after_reboot`), `certification_tags`.

## Socle technique commun

Une VM par apprenant, préparée par le `setup` de chaque lab :

- **Docker** et **Docker Compose** ;
- **Keycloak** et **PostgreSQL** en Compose, images épinglées
  `image:tag@sha256:…` (dernières versions stables **au moment d'écrire**, à
  relever sur le registre, jamais de `:latest`) ;
- **LLDAP** comme annuaire léger ;
- une **application témoin** (connexion OIDC) et une **API témoin** (jetons
  d'accès), écrites pour le catalogue, versionnées dans le dépôt ;
- pour le lab SAML, un **fournisseur de service témoin** à choisir (à
  vérifier : maintenu, épinglable).

## Règles qui s'appliquent

- **Validation sur l'état, jamais sur les commandes tapées** : les tests
  interrogent Keycloak (API d'administration, endpoints OIDC), l'annuaire
  (`ldapsearch`) et les applications témoins.
- **Titre identique** dans `lab.fr.yaml` et dans le bloc `<Lab>` de la leçon.
- **`doc_url` = la page qui héberge le bloc** (règle D) ; à repointer si la
  leçon bouge.
- **Câblage** (règle C) : section `## Mettre en pratique` de la leçon, un
  paragraphe qui dit ce que le lab fait faire et sur quoi porte la validation,
  puis `<Lab repo="iam-dsoxlab-training" title="…" id="…" env="VM" duree="~N min" />`.
  La `duree` alimente le volume horaire de la formation : la mesurer en jouant
  le lab, ne pas l'estimer.
- **Commits en local** dans le dépôt de labs ; la livraison est un geste de
  Stéphane.
- Chaque lab est joué en entier (setup, solution, tests, cas d'échec) avant
  d'être câblé, et reçoit un verdict daté dans `validation-labs.json`.

## Liste des labs

Une fiche par lab dans `fiches/`. Les numéros 11 à 14 ont été ajoutés après la
seconde lecture du challenger ; l'**ordre de jeu suit le parcours** du cadrage
(§5), pas la numérotation : 11 et 12 se jouent au module 4, 13 au module 6,
14 au module 7. Les deux épreuves sont **différées avec le catalogue** (écart
connu à la règle F, consigné dans le cadrage).

| # | Identifiant | Titre (FR) | Leçon d'accueil | Compétence | Statut leçon |
|---|---|---|---|---|---|
| 1 | `iam-01-annuaire-lldap` | Monter un annuaire et y organiser les comptes | `lldap` | `iam.federation.broker` | existe |
| 2 | `iam-02-keycloak-installer` | Installer Keycloak avec sa base de données | `keycloak/installation` | `iam.idp.deploy` | existe |
| 3 | `iam-03-federation-ldap` | Fédérer l'annuaire à Keycloak | `keycloak/federation-ldap` | `iam.federation.broker` | existe |
| 4 | `iam-04-client-oidc-pkce` | Connecter une application en OIDC avec PKCE | `keycloak/securiser-application-oidc` | `iam.sso.integrate` | existe |
| 5 | `iam-05-api-protegee` | Protéger une API par jetons d'accès | « Protéger une API » | `iam.api.protect` | **à écrire** |
| 6 | `iam-06-federation-saml` | Fédérer une application en SAML | `fondamentaux/saml` | `iam.sso.integrate` | existe |
| 7 | `iam-07-mfa-keycloak` | Imposer une authentification forte | « MFA et flows dans Keycloak » | `iam.auth.harden` | **à écrire** |
| 8 | `iam-08-depart-collaborateur` | Traiter le départ d'un collaborateur | « Cycle de vie et revue des accès » | `iam.access.govern` | **à écrire** |
| 9 | `iam-09-sauvegarde-montee-version` | Sauvegarder Keycloak et le mettre à jour | « Keycloak en production » | `iam.idp.operate` | **à écrire** |
| 10 | `iam-10-realm-as-code` | Décrire un realm en tant que code | « Configuration en tant que code » | `iam.idp.operate` | **à écrire** |
| 11 | `iam-11-federation-externe` | Déléguer la connexion à un fournisseur d'identité externe | « Fédération entrante » | `iam.federation.broker` | **à écrire** |
| 12 | `iam-12-depanner-integration` | Dépanner une intégration OIDC qui échoue | « Dépanner une intégration OIDC et SAML » | `iam.sso.integrate` | **à écrire** |
| 13 | `iam-13-revue-des-acces` | Automatiser le cycle de vie et conduire une revue des accès | « Revue des accès et automatisation » | `iam.access.govern` | **à écrire** |
| 14 | `iam-14-plateforme` | Brancher Kubernetes et un outil sur le fournisseur d'identité | « Kubernetes, Vault et les outils » | `iam.platform.integrate` | **à écrire** |
| E1 | `iam-epreuve-n1` | Épreuve de niveau 1 : brancher une application et une API | épreuve du niveau 1 | niveau 1 | **à écrire** |
| E2 | `iam-epreuve` | Épreuve : une identité de bout en bout | `fondamentaux/capstone` | toutes | **brouillon à finir** |

Identifiants de compétences alignés sur le cadrage v2 (§4) et **provisoires** tant que le
skills-guardian ne les a pas créés ; les mettre à jour ici le jour où ils
existent.

## Quand on s'y remet

1. Relire ce dossier et le cadrage, et vérifier que les leçons d'accueil
   existent toujours aux mêmes URL.
2. Créer le dépôt à partir du modèle Linux, `meta.yml` d'abord.
3. Écrire puis jouer les labs **dans l'ordre**, un par un, sur VM.
4. Câbler chaque lab dans sa leçon, avec sa durée mesurée.
5. `python3 scripts/audit-formation.py --parcours <slug>` pour mesurer
   l'écart restant.
