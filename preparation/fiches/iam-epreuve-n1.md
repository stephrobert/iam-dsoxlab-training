# iam-epreuve-n1 : Épreuve de niveau 1 : brancher une application et une API

| Champ | Valeur |
|---|---|
| Leçon d'accueil (`doc_url`) | `/docs/services/identite/epreuve-niveau-1/` |
| Compétence (provisoire) | `iam.idp.deploy, iam.sso.integrate, iam.api.protect, iam.federation.broker` |
| Durée visée | ~90 min (à **mesurer** en jouant le lab) |
| Prérequis | labs 1 à 6, 11 et 12 |
| Environnement | VM (`runtime.type: vm`), socle du README |

## Objectif

Sans indice, mettre en service un IdP, y fédérer l'annuaire, et brancher l'application et l'API témoins.

## Ce que l'apprenant fait

- installe Keycloak durable
- fédère l'annuaire
- connecte l'application témoin en OIDC avec PKCE
- protège l'API témoin (audience, scope, service en client credentials)

## État vérifié par les tests

- les états vérifiés des labs 2, 3, 4 et 5, réunis
- chronométré, sans `hints.yaml`

## Cas d'échec à prévoir dans les tests

- les cas d'échec des labs correspondants

## Indices (`hints.yaml`)

- aucun : c'est une mesure

## À vérifier avant d'écrire

- barème et durée à fixer après avoir joué l'épreuve en entier
