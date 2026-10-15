# iam-11-federation-externe : Déléguer la connexion à un fournisseur d'identité externe

| Champ | Valeur |
|---|---|
| Leçon d'accueil (`doc_url`) | `/docs/services/identite/keycloak/federation-entrante/` |
| Compétence (provisoire) | `iam.federation.broker` |
| Durée visée | ~40 min (à **mesurer** en jouant le lab) |
| Prérequis | lab 2 |
| Environnement | VM (`runtime.type: vm`), socle du README |

## Objectif

Laisser les utilisateurs se connecter au realm avec un compte d'un fournisseur d'identité externe, et contrôler ce qui est importé.

## Ce que l'apprenant fait

- déclare un fournisseur d'identité externe dans le realm : un **second Keycloak** fourni par le setup (reproductible, gratuit) ou une **application OAuth GitHub**
- règle les mappeurs (e-mail, nom, groupe par défaut) et le premier login
- se connecte avec un compte externe

## État vérifié par les tests

- le fournisseur externe est déclaré et actif
- un compte externe obtient un compte lié dans le realm, dans le groupe par défaut
- aucun rôle d'administration n'est accordé par défaut

## Cas d'échec à prévoir dans les tests

- compte externe lié automatiquement à un compte local de même e-mail sans vérification
- rôle trop large accordé au premier login

## Indices (`hints.yaml`)

- le second Keycloak du setup joue l'entreprise partenaire

## À vérifier avant d'écrire

- noms des réglages de premier login dans la version retenue
