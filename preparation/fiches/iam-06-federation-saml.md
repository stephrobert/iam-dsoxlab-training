# iam-06-federation-saml : Fédérer une application en SAML

| Champ | Valeur |
|---|---|
| Leçon d'accueil (`doc_url`) | `/docs/services/identite/fondamentaux/saml/` |
| Compétence (provisoire) | `iam.sso.integrate` |
| Durée visée | ~50 min (à **mesurer** en jouant le lab) |
| Prérequis | lab 2 |
| Environnement | VM (`runtime.type: vm`), socle du README |

## Objectif

Échanger les métadonnées entre Keycloak et un fournisseur de service témoin, et faire passer les bons attributs.

## Ce que l'apprenant fait

- crée le client SAML à partir des métadonnées du fournisseur de service
- règle les assertions signées et le mappage `mail` et groupes
- installe les métadonnées de Keycloak côté fournisseur de service et se connecte

## État vérifié par les tests

- le client SAML existe avec l'identifiant d'entité attendu
- les assertions sont signées
- le fournisseur de service reçoit `mail` et les groupes
- la connexion aboutit

## Cas d'échec à prévoir dans les tests

- assertions non signées
- horloges décalées entre VM (assertion expirée)

## Indices (`hints.yaml`)

- un traceur SAML dans le navigateur montre l'assertion

## À vérifier avant d'écrire

- choix du fournisseur de service témoin (maintenu, épinglable)
