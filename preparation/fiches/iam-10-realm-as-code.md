# iam-10-realm-as-code : Décrire un realm en tant que code

| Champ | Valeur |
|---|---|
| Leçon d'accueil (`doc_url`) | `/docs/services/identite/keycloak/configuration-as-code/` |
| Compétence (provisoire) | `iam.idp.operate` |
| Durée visée | ~50 min (à **mesurer** en jouant le lab) |
| Prérequis | labs 2 et 4 |
| Environnement | VM (`runtime.type: vm`), socle du README |

## Objectif

Décrire le realm, ses clients et ses rôles dans des fichiers versionnés, l'appliquer, et détecter une modification faite à la main.

## Ce que l'apprenant fait

- décrit le realm `formation` dans l'outil retenu
- l'applique sur un Keycloak neuf
- modifie un réglage dans la console, puis rejoue l'outil pour revenir à l'état décrit

## État vérifié par les tests

- le realm appliqué correspond aux fichiers
- la dérive introduite à la main est corrigée par la réapplication
- aucun secret en clair dans les fichiers

## Cas d'échec à prévoir dans les tests

- secret de client écrit en clair
- fichiers appliqués sur le realm `master`

## Indices (`hints.yaml`)

- partir d'un export du realm pour écrire la première version

## À vérifier avant d'écrire

- outil à choisir : provider Terraform Keycloak ou keycloak-config-cli ; versions et maintien à vérifier
