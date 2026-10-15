# iam-14-plateforme : Brancher Kubernetes et un outil sur le fournisseur d'identité

| Champ | Valeur |
|---|---|
| Leçon d'accueil (`doc_url`) | `(leçon à écrire) « Kubernetes, Vault et les outils »` |
| Compétence (provisoire) | `iam.platform.integrate` |
| Durée visée | ~60 min (à **mesurer** en jouant le lab) |
| Prérequis | labs 2 et 4 ; prérequis Kubernetes (RBAC) et Vault |
| Environnement | VM (`runtime.type: vm`), socle du README |

## Objectif

Faire authentifier `kubectl` et un outil de la plateforme par l'IdP, avec des droits qui suivent les groupes.

## Ce que l'apprenant fait

- configure l'authentification OIDC du serveur d'API d'un cluster de test
- lie le groupe `devops` à un rôle RBAC
- branche un outil (méthode OIDC de Vault, ou Grafana) sur le même realm

## État vérifié par les tests

- `kubectl` obtient un jeton de l'IdP et agit selon le groupe
- un compte `lecteurs` est refusé en écriture
- l'outil accepte la connexion par l'IdP

## Cas d'échec à prévoir dans les tests

- groupe lié à `cluster-admin`
- claim de groupe absent du jeton (aucun droit)

## Indices (`hints.yaml`)

- le claim des groupes doit être demandé au client

## À vérifier avant d'écrire

- mécanisme d'authentification OIDC du serveur d'API dans la version de Kubernetes retenue (configuration structurée)
- cluster de test : kind ou k3d selon les règles du site
