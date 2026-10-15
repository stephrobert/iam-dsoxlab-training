# iam-05-api-protegee : Protéger une API par jetons d'accès

| Champ | Valeur |
|---|---|
| Leçon d'accueil (`doc_url`) | `/docs/services/identite/keycloak/proteger-une-api/` |
| Compétence (provisoire) | `iam.api.protect` |
| Durée visée | ~50 min (à **mesurer** en jouant le lab) |
| Prérequis | lab 4 |
| Environnement | VM (`runtime.type: vm`), socle du README |

## Objectif

Faire refuser par l'API témoin tout appel sans jeton valide, de la bonne audience et du bon scope, et donner à un service un accès machine sans utilisateur.

## Ce que l'apprenant fait

- déclare un scope `notes:lecture` et l'audience de l'API
- configure l'API témoin pour valider les jetons (JWKS, `iss`, `aud`, `exp`, scope)
- crée un client confidentiel en client credentials pour un service de sauvegarde

## État vérifié par les tests

- sans jeton : 401
- jeton d'une autre audience : 401 ou 403
- jeton sans le scope : 403
- jeton du service en client credentials : 200 sur la lecture, 403 sur l'écriture
- le secret du client n'apparaît dans aucun fichier versionné

## Cas d'échec à prévoir dans les tests

- API qui ne vérifie que la signature
- secret du client dans le Compose

## Indices (`hints.yaml`)

- décoder un jeton pour voir `aud` et `scope` avant de modifier l'API

## À vérifier avant d'écrire

- mécanisme d'audience dans Keycloak (mappeur d'audience) pour la version retenue
