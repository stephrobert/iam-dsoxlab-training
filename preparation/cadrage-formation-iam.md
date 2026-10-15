# Formation « Gestion des identités et des accès (IAM) » : cadrage v2

**Décision de Stéphane du 2026-10-15** (dette « Services ») : l'identité
devient une **nouvelle formation**, un module de fondamentaux puis un module
par outil, **Keycloak en référence** et **authentik en option**, pour les
métiers **DevSecOps** et **Platform Engineer**. Le même jour : « Les nouvelles
formations doivent devenir des références et donc posséder tous les chapitres
nécessaires. »

**Historique.** v1 le 2026-10-15, contestée le jour même par le challenger
(verdict NOT READY, huit corrections minimales). Cette v2 les applique toutes ;
les faits nouveaux qu'il apportait ont été **revérifiés à la source** (notes
de version Keycloak sur GitHub, voir §2). Seconde lecture du challenger le même jour : huit corrections appliquées,
trois derniers points obligatoires corrigés ensuite (prérequis du module 7,
dépannage au niveau 1, épreuves différées). Statut : **validé par Stéphane
le 2026-10-15** (D1 à D9, §7).

## 1. Inventaire : ce qui existe

22 pages sous `/docs/services/identite/`, **aucun quiz, aucun lab, aucune
compétence active** (mesure du 2026-10-15). Un **brouillon de compétences**
existe déjà : `src/data/competences/drafts/iam.yaml` (2026-10-05, issu de
l'alignement DSOMM), avec `iam.idp.deploy`, `iam.sso.integrate` et le bloc
candidat `identite-acces` : la table du §4 **repart de lui**.

| Page | Mots | État |
|---|---:|---|
| `identite/` (index) | 2131 | à réécrire en accueil ; promet FreeIPA (l.77, 208, 230) et cite un chiffre périmé (l.31) |
| `fondamentaux/bases-iam` | 2323 | publiée |
| `fondamentaux/autorisation` (RBAC, ABAC) | 2349 | à alléger : l.227-357 recoupent la formation Rego, l.358-435 le RBAC Kubernetes |
| `fondamentaux/ldap-annuaires` | 1901 | publiée |
| `fondamentaux/oauth2` | 2954 | erreurs à corriger (§8) |
| `fondamentaux/oidc` | 3599 | publiée, FAQ |
| `fondamentaux/saml` | 2668 | date de février |
| `fondamentaux/scim` | 2915 | **erreur bloquante** : l.465 nie le SCIM natif de Keycloak |
| `fondamentaux/mfa-webauthn` | 3341 | à aligner sur 800-63B-4 ; l.414-470 (Keycloak) à déplacer |
| `fondamentaux/securite-operationnelle` | 3231 | erreurs à corriger (§8) |
| `fondamentaux/capstone` | 1969 | **brouillon**, périmé (extension SCIM tierce, Keycloak 26.7.0) |
| `keycloak/` (concepts) | 3140 | publiée ; « Stratégie 3 » (fédération entrante) sans geste |
| `keycloak/installation` | 2013 | `tutorial: installation` ; version 26.7.0 périmée |
| `keycloak/administration` | 4550 | publiée |
| `keycloak/securiser-application-oidc` | 1997 | publiée |
| `keycloak/federation-ldap` | 1813 | publiée |
| `keycloak/kubernetes` (Operator) | 1968 | `tutorial: installation` ; version périmée |
| `keycloak/formation` | 1634 | redondante avec le plan (D3) |
| `authentik/comprendre` | 2599 | versions 2026.2.1 (2026.8.4 sortie) |
| `authentik/installation-docker-compose` | 2035 | `tutorial: installation` ; **images sans digest** |
| `lldap` | 1255 | `tutorial: prise-en-main` ; lien FreeIPA faux (l.21), mots-clés et description fautifs, pas de `toolVersion` |
| `freeipa` | 914 | **brouillon** d'avril 2025 |

Pages **d'autres formations** que celle-ci reprend sans les réécrire :
`services/architecture/identite-et-autorisation` (Architecture des services),
`securiser/secrets/identite-machine-workload-identity` (Secrets, DevSecOps,
Cloud), `cloud/securite/identifiants-temporaires`, `cloud/securite/iam`.

## 2. Étalonnage sur des référentiels externes

Lus à la source le 2026-10-15 sauf mention.

- **SFIA 9, IAMT** (« Identity and access management », compétence définitive
  de SFIA 9). Les métiers DevSecOps (`metiers/devsecops.yaml:69`) et Platform
  Engineer (`metiers/platform-engineer.yaml:72`) déclarent **IAMT 3** : c'est
  la **cible** (« Administers standard identity and access management
  services […] monitoring, audits and logging […] simple […] solutions »). Le
  niveau 4 (« integration […] with new technologies », solutions complexes)
  est approché par le module 7, sans être revendiqué.
- **CISSP, domaine 5** (plan en vigueur depuis le 15 avril 2024) : 5.1 accès
  physique et logique, 5.2 identification et authentification (personnes,
  appareils, services), 5.3 identité fédérée, 5.4 autorisation, 5.5 cycle de
  vie du provisioning, 5.6 systèmes d'authentification. Intitulés relevés sur
  des résumés tiers, **à confirmer sur le PDF officiel**. **5.1 (accès
  physique) est hors périmètre**, déclaré ici. 5.4 cite DAC, MAC, règles et
  risque : un paragraphe et des liens dans `autorisation`.
- **NIST SP 800-63-4**, final, **juillet 2025** (historique CSRC : 31/07/2025).
  800-63B-4 : à AAL2 le vérificateur **doit offrir** une option résistante au
  phishing ; AAL3 exige une clé **non exportable**, donc les
  **authentificateurs synchronisables** y sont **interdits** (permis à AAL2) ;
  mots de passe : **15 caractères** seuls, 8 en multifacteur, **aucune règle
  de composition**, **aucune rotation périodique** imposée.
- **OAuth** : la référence publiée est la **RFC 9700** (bonnes pratiques de
  sécurité, BCP, janvier 2025) ; **OAuth 2.1 reste un brouillon IETF**
  (révision 16 du 2026-09-03, vérifiée par le challenger sur l'API du
  datatracker). Extensions à
  traiter dans les leçons existantes : device authorization grant (RFC 8628),
  token exchange (RFC 8693), jetons liés DPoP (RFC 9449) ou mTLS (RFC 8705).
- **Keycloak**, notes de version officielles relues : **26.8.0** (2026-10-01)
  passe l'**API SCIM** de préversion à « supported » ; **26.6** passe les
  **Workflows** à « supported » (« bringing key capabilities of Identity
  Governance and Administration (IGA) to Keycloak ») ; dernière version
  **26.8.1** (2026-10-13). Passkeys natives « supported » depuis 26.4.0 (vérifié par le challenger
  dans les notes de version) ; Organizations : à confirmer par le
  fact-checker.

## 3. Prérequis de la formation

Ancrés sur des compétences et pages existantes, à afficher dans l'accueil :

| Prérequis | Pourquoi ici | Où l'apprendre |
|---|---|---|
| HTTP : redirections, cookies, en-têtes | tout flux OAuth/OIDC/SAML est une suite de redirections | `/docs/reseaux/fondamentaux/http-https/`, `network.http.troubleshoot` |
| TLS et certificats | jetons signés, IdP en HTTPS | `network.tls.troubleshoot` |
| DNS et nom d'hôte | piège n°1 de Keycloak (hostname) | `network.dns.troubleshoot` |
| JSON | jetons, Discovery, API | `data.json.*` |
| Conteneurs et Compose | tous les exercices | `container.run` (compétence Compose : **à vérifier**) |
| curl | observer un flux, appeler une API | `/docs/admin-serveurs/linux/references/curl/` |
| Kubernetes, RBAC compris | module 7 (OIDC du serveur d'API) et leçon Operator | formation Kubernetes, `/docs/conteneurs/orchestrateurs/kubernetes/rbac/` |
| Bases de Vault | module 7 (méthode d'authentification OIDC) | formation Gestion des secrets |

## 4. Compétences proposées (repart de `drafts/iam.yaml`)

Cible **IAMT 3**. Délimitation avec l'existant : `cloud.access.design`
(concevoir l'accès dans un **cloud**, recertification comprise) ;
`sec.secrets.identity` et `cloud.workload.identity` (identité **machine**) ;
`k8s.serviceaccount.configure`. Les compétences ci-dessous portent sur
l'identité **humaine** et le **fournisseur d'identité**.

| Identifiant | Origine | Geste observable | Livrable observable |
|---|---|---|---|
| `iam.idp.deploy` | brouillon | mettre en service un IdP persistant, créer un realm, ses utilisateurs, groupes, rôles, journaux d'événements | Keycloak sur PostgreSQL qui survit au redémarrage |
| `iam.sso.integrate` | brouillon, élargi | brancher une application en OIDC (PKCE) ou SAML, valider ses jetons, **dépanner** l'intégration | application témoin connectée, jetons validés |
| `iam.api.protect` | nouveau | protéger une API : audience, scopes, client credentials | API qui refuse jeton absent, mauvaise audience, mauvais scope |
| `iam.federation.broker` | nouveau | relier l'IdP à des sources d'identité externes : annuaire LDAP, IdP tiers (Entra ID, Google, GitHub) | connexion d'un compte de l'annuaire et d'un compte externe |
| `iam.auth.harden` | nouveau | imposer une authentification forte résistante au phishing, politique de mot de passe conforme 800-63B-4 | flow qui exige le second facteur au bon groupe |
| `iam.access.govern` | nouveau | automatiser arrivée, mobilité, départ (SCIM natif, Workflows) et conduire une revue des accès | départ traité (compte, sessions, groupes) et revue produite |
| `iam.platform.integrate` | nouveau | brancher l'IdP sur Kubernetes, Vault et les outils, ou derrière un proxy d'authentification | `kubectl` et un outil authentifiés par l'IdP |
| `iam.idp.operate` | nouveau, **scindé de deploy** | exploiter l'IdP en production : reverse proxy, TLS, haute disponibilité, sauvegarde, montée de version, configuration en tant que code, surveillance | restauration prouvée, montée de version sans perte, realm décrit en code |

Questions pour le skills-guardian : faut-il une compétence pour les
fondamentaux (`bases-iam`, `autorisation`, crypto), ou sont-ils les sources
d'appui des autres ? Où vit LLDAP (pratique de `iam.federation.broker`) ?
Rattachement à l'**Administrateur Linux** : le brouillon cite une ancienne
décision (`src/data/metiers/administrateur-linux.yaml`, Keycloak « lacune
volontaire ») dont le fichier **n'existe plus** (métiers v4 dans
`src/data/competences/metiers/`) : à reposer (D9).

## 5. Parcours v2 : deux niveaux, pratique dès le module 2

La v1 alignait cinq modules de concepts avant le premier IdP. Ici, Keycloak
tourne dès le module 2, et chaque flux est **observé** (curl, jeton décodé)
avant d'être expliqué en détail.

| Module | Leçons existantes | À écrire (**n**) ou à regrouper (**r**) |
|---|---|---|
| Accueil | `identite/` réécrit (prérequis, niveaux, sans FreeIPA) | |
| **Niveau 1 : brancher une application sur un IdP** | | |
| 1. Comprendre | bases-iam, autorisation (allégée, DAC/MAC, liens Rego et RBAC) | **n** Bases cryptographiques des jetons (signature asymétrique, X.509, base64url, JWS) |
| 2. Premier fournisseur d'identité | keycloak/ (concepts), keycloak/installation, keycloak/administration | |
| 3. OAuth 2 et OpenID Connect | oauth2, oidc, keycloak/securiser-application-oidc | **r** Jetons et sessions (oidc l.389-435, oauth2 l.306-381, securite-operationnelle l.170-180 et 348-394, bases-iam l.183-238 ; refresh, révocation, déconnexion, DPoP/mTLS) ; **r** Protéger une API (étapes 5-6 de securiser-application-oidc, client credentials, device grant, token exchange ; cite `mcp-oauth`) |
| 4. Fédération et annuaires | saml, ldap-annuaires, lldap, keycloak/federation-ldap | **n** Fédération entrante (identity brokering ; IdP externe reproductible sans compte payant : second Keycloak ou application OAuth GitHub) ; **n** Dépanner une intégration OIDC et SAML (au niveau 1, puisque `iam.sso.integrate` et l'épreuve 1 la mesurent) |
| Épreuve niveau 1 | | **n** application et API branchées sans indice |
| **Niveau 2 : exploiter et gouverner** | | |
| 5. Authentification forte | mfa-webauthn (concept, aligné 800-63B-4) | **r** MFA, passkeys et flows dans Keycloak (mfa-webauthn l.414-470 déplacées) |
| 6. Cycle de vie et gouvernance | scim (corrigé) | **n** Revue des accès et automatisation (Workflows, SCIM natif) ; délimitée face à `cloud/securite/iam` l.680-710, qui enseigne déjà arrivée, mobilité, départ et recertification côté cloud |
| 7. Brancher la plateforme | identité des workloads : **leçon partagée** `securiser/secrets/identite-machine-workload-identity` | **n** Kubernetes, Vault et les outils (OIDC du serveur d'API, méthode OIDC de Vault, Grafana/GitLab/Argo CD, proxy d'authentification ; cite `traefik-securite`, `pomerium`, `dex`) |
| 8. Sécuriser et exploiter | securite-operationnelle (avancée avant la production), keycloak/kubernetes | **n** Keycloak en production (reverse proxy, hostname, TLS, console d'administration, comptes de secours, panne de l'IdP, haute disponibilité, sauvegarde, montée de version ; reprend les pièges de `keycloak/formation`) ; **n** Configuration en tant que code |
| 9. authentik (facultatif) | authentik/comprendre, authentik/installation-docker-compose | |
| Épreuve niveau 2 | capstone réécrit (SCIM natif, version courante) | |

Bilan, recompté : **29 leçons** hors accueil et épreuves, dont **7 à écrire** et
**3 regroupements** (chacun une page neuve), plus **2 épreuves** (la première
est une page neuve, la seconde le capstone réécrit).

**Écart connu à la règle F** : la règle veut que chaque épreuve existe dans le
catalogue de labs ; le catalogue étant **reporté** (D1), les deux épreuves sont
**différées avec lui**. Leurs pages décrivent l'épreuve ; leur passage outillé
viendra avec le catalogue (fiches `iam-epreuve-n1` et `iam-epreuve` de
`todo/labs-iam/`). **Hors formation, cités** : PAM (Teleport,
certificats SSH de la formation Secrets ; ne pas confondre avec les modules
PAM de Linux de `/docs/securiser/durcissement/pam/`), IAM cloud, Dex.

**Champs `tutorial` à retirer** (une leçon n'est jamais un tutoriel,
`check-frontieres`) : `keycloak/installation`, `keycloak/kubernetes`,
`authentik/installation-docker-compose`, `lldap`. Ces pages sortent du
catalogue `/tutoriels/`.

## 6. Labs

**D1 tranchée** (Stéphane, 2026-10-15) : catalogue reporté. Toute procédure
nouvelle est **rejouée par le lab-validator** avant publication (règle B). Le
dossier `todo/labs-iam/` garde la liste, le socle et une fiche par lab ; le
lab de départ d'un collaborateur s'appuie sur le **SCIM natif et les
Workflows** de Keycloak.

## 7. Décisions à trancher

**Toutes tranchées par Stéphane le 2026-10-15**, chacune selon la
recommandation ci-dessous (D2 à D7 acceptées en bloc).

- **D2, FreeIPA** : **retirer** de la formation (brouillon d'avril 2025, hors
  cible) et retirer les promesses de l'index. Challenger : d'accord.
- **D3, `keycloak/formation`** : **301 vers l'accueil**, ses pièges reversés
  dans « Keycloak en production ». Challenger : d'accord.
- **D4, `lldap`** : **leçon** du module 4 (pratique de l'annuaire), donc retrait
  de son champ `tutorial` comme pour les trois autres pages. Challenger :
  d'accord.
- **D5, authentik** : **module facultatif de découverte**, pas une option de
  compétence (sinon cinq leçons de plus à écrire pour authentik). Challenger :
  d'accord.
- **D6, PAM** : **citer**, pas de module. Challenger : d'accord.
- **D7, emplacement** : **garder** `/docs/services/identite/`, aucune
  redirection. Challenger : d'accord.
- **D8, niveaux** : **deux niveaux** avec épreuve chacun (§5).
- **D9, Administrateur Linux** : **seulement l'annuaire** :
  `iam.federation.broker` lui est rattachée ; le reste de l'IAM vise DevSecOps
  et Platform Engineer.

## 8. Corrections factuelles à confier au fact-checker

Relevées par le challenger, à vérifier puis corriger **dans les pages**
(relecture complète de chacune) :

- `scim.mdx:465` nie le SCIM natif de Keycloak : **faux** depuis 26.8.0
  (vérifié).
- Versions Keycloak 26.7.0 dans `installation:216`, `kubernetes:29,85`,
  `capstone:64,87` (26.8.1 courante, vérifié) ; authentik 2026.2.1 (2026.8.4
  selon le challenger) ; LLDAP sans `toolVersion`.
- `authentik/installation-docker-compose:157,175,198` : images sans digest.
- `oauth2` : rotation des refresh tokens (l.344-346, 405) ; PKCE « obligatoire
  depuis OAuth 2.1 » et flows « officiellement retirés » (l.42, 270, 285,
  431) alors que 2.1 est un brouillon : s'appuyer sur RFC 9700 ; référence
  `draft-ietf-oauth-security-topics` (l.444-445) devenue RFC 9700 ; révision
  du brouillon (l.409).
- `securite-operationnelle:492` cite 800-63-3 ; l.152 exemple
  `aud.includes('my-api')` trompeur (accepte `my-api-admin`) ; l.177
  `SameSite=Strict` partout casse le retour de l'IdP ; l.176 durées de session
  à aligner sur 800-63B-4.
- `mfa-webauthn:303` « Passkeys AAL2-3 » contredit 800-63B-4 ; l.142 date
  (juillet, pas août 2025) ; l.247 toutes les passkeys ne sont pas
  synchronisées.
- Durées contradictoires entre pages : access token (`oauth2:392`,
  `oidc:434`, `securite-operationnelle:131`), renouvellement des clés
  (`securite-operationnelle:189`, `capstone:487`) : une valeur sourcée, une
  seule.
- `index.mdx:31` (74 %, DBIR 2023) contredit `mfa-webauthn:72` ; l.169 SMS
  en exemple de MFA ; l.195 « SSO et MFA émergent avec le cloud ».
- `lldap.mdx` l.3, l.10-13, l.21.

## 9. Ordre d'exécution après validation

1. (fait) Challenger, deux lectures ; Stéphane, D1 à D9.
2. Skills-guardian : parcours YAML, registre, « Mon parcours », compétences
   (depuis `drafts/iam.yaml`), rattachements aux métiers.
3. Fact-checker : la liste du §8, plus les faits nouveaux du §2.
4. Author : regroupements, puis leçons nouvelles ; lab-validator sur chaque
   procédure avant publication ; quiz de chaque leçon.
5. Reviewer, puis challenger sur la formation entière.
