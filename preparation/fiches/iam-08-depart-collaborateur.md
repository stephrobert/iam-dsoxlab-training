# iam-08-depart-collaborateur : Traiter le départ d'un collaborateur

| Champ | Valeur |
|---|---|
| Leçon d'accueil (`doc_url`) | `/docs/services/identite/keycloak/revue-des-acces/` |
| Compétence (provisoire) | `iam.access.govern` |
| Durée visée | ~40 min (à **mesurer** en jouant le lab) |
| Prérequis | labs 3 et 4 |
| Environnement | VM (`runtime.type: vm`), socle du README |

## Objectif

Couper tous les accès d'une personne qui part, sessions comprises, et produire la preuve de la revue.

## Ce que l'apprenant fait

- désactive le compte à la source (annuaire)
- révoque ses sessions et jetons actifs dans Keycloak (ou laisse un Workflow le faire sur l'événement de désactivation)
- retire ses groupes
- exporte la liste des accès restants du realm pour la revue

## État vérifié par les tests

- le compte est désactivé côté annuaire et côté Keycloak après synchronisation
- aucune session active pour ce compte
- son jeton de rafraîchissement est refusé
- le fichier de revue liste les comptes et leurs groupes

## Cas d'échec à prévoir dans les tests

- compte désactivé mais session encore valide
- compte supprimé au lieu de désactivé (perte de traçabilité)

## Indices (`hints.yaml`)

- les sessions d'un utilisateur se voient et se révoquent depuis sa fiche

## À vérifier avant d'écrire

- Keycloak 26.8.0 (2026-10-01) a une **API SCIM native** (passée de préversion à « supported ») et, depuis 26.6, des **Workflows** de gouvernance (cycle de vie automatisé, YAML) : vérifié dans les notes de version officielles le 2026-10-15. Le lab s'appuie sur eux, pas sur une extension tierce ; relire la doc « Managing users and groups through SCIM » de la version retenue
