# iam-03-federation-ldap : Fédérer l'annuaire à Keycloak

| Champ | Valeur |
|---|---|
| Leçon d'accueil (`doc_url`) | `/docs/services/identite/keycloak/federation-ldap/` |
| Compétence (provisoire) | `iam.federation.broker` |
| Durée visée | ~40 min (à **mesurer** en jouant le lab) |
| Prérequis | labs 1 et 2 (le setup les reconstruit) |
| Environnement | VM (`runtime.type: vm`), socle du README |

## Objectif

Brancher LLDAP comme fédération d'utilisateurs de Keycloak, en lecture seule, groupes compris.

## Ce que l'apprenant fait

- déclare la fédération LDAP dans le realm `formation` (URL, DN de liaison, branche des utilisateurs)
- ajoute le mappeur de groupes
- lance une synchronisation et se connecte avec un compte de l'annuaire

## État vérifié par les tests

- la fédération existe, en mode lecture seule
- les trois comptes de l'annuaire sont connus de Keycloak
- les groupes `devops` et `lecteurs` sont importés avec leurs membres
- un compte de l'annuaire obtient un jeton sur le realm

## Cas d'échec à prévoir dans les tests

- mode écriture laissé actif (Keycloak modifierait l'annuaire)
- mappeur de groupes absent : utilisateurs sans groupes

## Indices (`hints.yaml`)

- tester la connexion et l'authentification depuis l'écran de fédération avant de sauvegarder

## À vérifier avant d'écrire

- noms des champs de la fédération dans la version de Keycloak retenue
