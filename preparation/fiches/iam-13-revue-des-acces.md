# iam-13-revue-des-acces : Automatiser le cycle de vie et conduire une revue des accès

| Champ | Valeur |
|---|---|
| Leçon d'accueil (`doc_url`) | `/docs/services/identite/keycloak/revue-des-acces/` |
| Compétence (provisoire) | `iam.access.govern` |
| Durée visée | ~45 min (à **mesurer** en jouant le lab) |
| Prérequis | labs 2 et 8 |
| Environnement | VM (`runtime.type: vm`), socle du README |

## Objectif

Faire appliquer par Keycloak les règles de cycle de vie et produire une revue des accès exploitable.

## Ce que l'apprenant fait

- écrit un Workflow qui désactive un compte inactif depuis N jours et prévient
- provisionne un utilisateur par l'API SCIM native
- exporte les comptes, leurs groupes et leurs rôles pour la revue, et retire un accès injustifié

## État vérifié par les tests

- le Workflow existe et se déclenche sur le compte inactif de test
- l'utilisateur créé par SCIM existe avec ses groupes
- le fichier de revue est complet et l'accès injustifié a disparu

## Cas d'échec à prévoir dans les tests

- Workflow qui supprime au lieu de désactiver
- revue qui oublie les rôles accordés directement hors groupe

## Indices (`hints.yaml`)

- les Workflows se décrivent en YAML

## À vérifier avant d'écrire

- syntaxe des Workflows et chemin de l'API SCIM dans la version retenue (26.6 et 26.8 au moins)
