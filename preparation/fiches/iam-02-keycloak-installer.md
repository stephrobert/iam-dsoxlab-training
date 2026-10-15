# iam-02-keycloak-installer : Installer Keycloak avec sa base de données

| Champ | Valeur |
|---|---|
| Leçon d'accueil (`doc_url`) | `/docs/services/identite/keycloak/installation/` |
| Compétence (provisoire) | `iam.idp.deploy` |
| Durée visée | ~40 min (à **mesurer** en jouant le lab) |
| Prérequis | aucun |
| Environnement | VM (`runtime.type: vm`), socle du README |

## Objectif

Faire tourner Keycloak en mode production minimal, adossé à PostgreSQL, avec un compte d'administration qui n'est pas le compte de démarrage.

## Ce que l'apprenant fait

- écrit le Compose Keycloak + PostgreSQL (volumes, variables de base de données, nom d'hôte)
- démarre Keycloak, crée un realm `formation` et un administrateur nominatif
- supprime ou désactive l'administrateur temporaire de démarrage

## État vérifié par les tests

- Keycloak répond, endpoint de santé au vert
- la base est PostgreSQL, pas la base de développement
- le realm `formation` existe et survit au redémarrage des conteneurs
- l'administrateur temporaire n'existe plus ou est désactivé

## Cas d'échec à prévoir dans les tests

- Keycloak lancé en `start-dev` (base embarquée, données perdues)
- hostname mal réglé derrière le port exposé

## Indices (`hints.yaml`)

- la différence `start` / `start-dev` est expliquée dans la leçon
- l'endpoint de santé est sur le port de gestion

## À vérifier avant d'écrire

- version stable de Keycloak au moment d'écrire, et port de gestion (9000) selon cette version
- nom exact des variables d'environnement de l'administrateur initial dans cette version
