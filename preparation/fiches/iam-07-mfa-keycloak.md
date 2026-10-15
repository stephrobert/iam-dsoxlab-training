# iam-07-mfa-keycloak : Imposer une authentification forte

| Champ | Valeur |
|---|---|
| Leçon d'accueil (`doc_url`) | `/docs/services/identite/keycloak/mfa-flows/` |
| Compétence (provisoire) | `iam.auth.harden` |
| Durée visée | ~45 min (à **mesurer** en jouant le lab) |
| Prérequis | lab 4 |
| Environnement | VM (`runtime.type: vm`), socle du README |

## Objectif

Exiger un second facteur pour le groupe `devops`, avec une option résistante au phishing, sans bloquer les autres comptes.

## Ce que l'apprenant fait

- copie le flow de navigateur et y ajoute une étape conditionnelle pour le groupe `devops`
- active OTP et WebAuthn (passkey) comme seconds facteurs
- rend la politique de mot de passe conforme à NIST SP 800-63B-4 (longueur, pas de composition imposée, pas d'expiration périodique)

## État vérifié par les tests

- le flow actif exige un second facteur pour `devops`, pas pour `lecteurs`
- WebAuthn est proposé
- la politique de mot de passe n'impose ni composition ni expiration
- un compte `devops` sans second facteur enregistré doit en enregistrer un à la connexion

## Cas d'échec à prévoir dans les tests

- flow par défaut modifié directement (irréversible sans sauvegarde)
- second facteur exigé pour tous, administrateur compris, sans secours

## Indices (`hints.yaml`)

- tester avec un navigateur privé et un compte de chaque groupe

## À vérifier avant d'écrire

- noms des étapes conditionnelles et des politiques dans la version retenue
- les exigences 800-63B-4 citées (relevées le 2026-10-15)
