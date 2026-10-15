# iam-epreuve : Épreuve : une identité de bout en bout

| Champ | Valeur |
|---|---|
| Leçon d'accueil (`doc_url`) | `/docs/services/identite/fondamentaux/capstone/ (brouillon à finir)` |
| Compétence (provisoire) | `toutes les compétences de la formation` |
| Durée visée | ~120 min (à **mesurer** en jouant le lab) |
| Prérequis | tous les labs |
| Environnement | VM (`runtime.type: vm`), socle du README |

## Objectif

Sans indice, mettre en service un fournisseur d'identité complet et en prouver le fonctionnement par l'état du système.

## Ce que l'apprenant fait

- installe Keycloak durable, fédère l'annuaire
- connecte l'application témoin (OIDC, PKCE) et protège l'API témoin
- impose l'authentification forte au groupe sensible
- traite un départ et produit la revue des accès
- laisse une sauvegarde restaurable

## État vérifié par les tests

- tous les états vérifiés des labs 2 à 9, réunis
- chronométré, sans `hints.yaml`

## Cas d'échec à prévoir dans les tests

- les cas d'échec des labs précédents

## Indices (`hints.yaml`)

- aucun : c'est une mesure

## À vérifier avant d'écrire

- barème et durée à fixer après avoir joué l'épreuve en entier
