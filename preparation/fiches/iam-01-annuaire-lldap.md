# iam-01-annuaire-lldap : Monter un annuaire et y organiser les comptes

| Champ | Valeur |
|---|---|
| Leçon d'accueil (`doc_url`) | `/docs/services/identite/lldap/` |
| Compétence (provisoire) | `iam.federation.broker` |
| Durée visée | ~30 min (à **mesurer** en jouant le lab) |
| Prérequis | aucun (premier lab) |
| Environnement | VM (`runtime.type: vm`), socle du README |

## Objectif

Démarrer un annuaire LDAP léger et y ranger des comptes et des groupes qu'un fournisseur d'identité pourra lire.

## Ce que l'apprenant fait

- démarre LLDAP en Docker Compose sur la VM
- crée une unité pour les personnes et une pour les groupes, trois utilisateurs et deux groupes (`devops`, `lecteurs`)
- interroge l'annuaire avec `ldapsearch` pour vérifier l'appartenance

## État vérifié par les tests

- LLDAP répond sur son port LDAP et son interface web
- les trois comptes existent avec leur `mail` et leur `cn`
- l'appartenance aux groupes est exacte (`memberOf` ou équivalent LLDAP)
- les données survivent à un `docker compose restart`

## Cas d'échec à prévoir dans les tests

- un compte créé hors de la bonne branche
- mot de passe administrateur laissé par défaut

## Indices (`hints.yaml`)

- lire le DN de base dans la configuration LLDAP avant d'écrire la requête
- `ldapsearch -x -H ldap://… -D … -W -b …`

## À vérifier avant d'écrire

- schéma exposé par la version de LLDAP retenue (attribut d'appartenance)
- image LLDAP épinglée par digest
