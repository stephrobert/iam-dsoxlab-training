# Les `doc_url` des seize labs, confrontés au site

Relevé le 2026-10-16 contre `main` du dépôt du site (`f6d8e637f`).

**Les seize leçons existent.** Le brief en donnait huit pour « à écrire » :
la branche de la formation a été fusionnée dans `main` depuis sa rédaction.
Aucun lab n'a donc besoin d'un `doc_url` provisoire.

Les pages répondent encore 404 en ligne, le site n'ayant pas été redéployé.
C'est sans effet sur les labs, mais `dsoxlab validate-structure --check-urls`
échouera tant que le déploiement n'a pas eu lieu : ce contrôle est le seul du
validateur qui sorte sur le réseau, et il se joue après la publication.

L'ordre est celui du JEU, fixé par le cadrage de la formation, et non la
numérotation des fiches.

| Ordre | Lab | Titre du lab | `doc_url` | Leçon qui hébergera le bloc |
|---|---|---|---|---|
| 1 | `iam-02-keycloak-installer` | Installer Keycloak avec sa base de données | `/docs/services/identite/keycloak/installation/` | Installer Keycloak avec Docker |
| 2 | `iam-04-client-oidc-pkce` | Connecter une application en OIDC avec PKCE | `/docs/services/identite/keycloak/securiser-application-oidc/` | Sécuriser une application avec Keycloak (OIDC) |
| 3 | `iam-05-api-protegee` | Protéger une API par jetons d'accès | `/docs/services/identite/keycloak/proteger-une-api/` | Protéger une API par jetons d'accès avec Keycloak |
| 4 | `iam-01-annuaire-lldap` | Monter un annuaire et y organiser les comptes | `/docs/services/identite/lldap/` | Monter un annuaire LDAP léger avec LLDAP |
| 5 | `iam-03-federation-ldap` | Fédérer l'annuaire à Keycloak | `/docs/services/identite/keycloak/federation-ldap/` | Fédérer un annuaire LDAP ou AD avec Keycloak |
| 6 | `iam-06-federation-saml` | Fédérer une application en SAML | `/docs/services/identite/fondamentaux/saml/` | SAML 2.0 : la fédération enterprise |
| 7 | `iam-11-federation-externe` | Déléguer la connexion à un fournisseur d'identité externe | `/docs/services/identite/keycloak/federation-entrante/` | Fédération entrante : déléguer la connexion à un IdP |
| 8 | `iam-12-depanner-integration` | Dépanner une intégration OIDC qui échoue | `/docs/services/identite/keycloak/depanner-integration/` | Dépanner une intégration OIDC et SAML avec Keycloak |
| E1 | `iam-epreuve-n1` | Épreuve de niveau 1 : brancher une application et une API | `/docs/services/identite/epreuve-niveau-1/` | Épreuve niveau 1 : brancher une application et une API sur Keycloak |
| 9 | `iam-07-mfa-keycloak` | Imposer une authentification forte | `/docs/services/identite/keycloak/mfa-flows/` | MFA, passkeys et flows d'authentification dans Keycloak |
| 10 | `iam-08-depart-collaborateur` | Traiter le départ d'un collaborateur | `/docs/services/identite/keycloak/revue-des-acces/` | Revue des accès et cycle de vie dans Keycloak |
| 11 | `iam-13-revue-des-acces` | Automatiser le cycle de vie et conduire une revue des accès | `/docs/services/identite/keycloak/revue-des-acces/` | Revue des accès et cycle de vie dans Keycloak |
| 12 | `iam-14-plateforme` | Brancher Kubernetes et un outil sur le fournisseur d'identité | `/docs/services/identite/keycloak/plateforme/` | Brancher Kubernetes et Vault sur Keycloak (OIDC) |
| 13 | `iam-09-sauvegarde-montee-version` | Sauvegarder Keycloak et le mettre à jour | `/docs/services/identite/keycloak/production/` | Exploiter Keycloak en production : proxy, sauvegarde, montée |
| 14 | `iam-10-realm-as-code` | Décrire un realm en tant que code | `/docs/services/identite/keycloak/configuration-as-code/` | Décrire un realm Keycloak en code avec Terraform |
| E2 | `iam-epreuve` | Épreuve : une identité de bout en bout | `/docs/services/identite/epreuve-niveau-2/` | Épreuve niveau 2 : exploiter et gouverner un fournisseur d'identité |

## Deux fiches corrigées au passage

- `iam-14-plateforme` portait « (leçon à écrire) » alors que
  `keycloak/plateforme.mdx` existe ;
- `iam-epreuve` pointait `fondamentaux/capstone/`, qui n'existe pas : la page
  est `epreuve-niveau-2.mdx`.

## Ce qui reste à remplir

La **durée mesurée** de chaque lab, qui ne s'estime pas : elle se relève en
jouant le lab, et elle alimente le volume horaire de la formation. La colonne
sera ajoutée au fur et à mesure, avec le verdict de `validation-labs.json`.

Deux labs partagent une leçon, et c'est voulu : `iam-08-depart-collaborateur`
et `iam-13-revue-des-acces` s'accrochent tous deux à `keycloak/revue-des-acces`,
le premier sur le départ d'un collaborateur, le second sur la revue elle-même.

