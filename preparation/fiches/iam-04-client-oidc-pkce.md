# iam-04-client-oidc-pkce : Connecter une application en OIDC avec PKCE

| Champ | Valeur |
|---|---|
| Leçon d'accueil (`doc_url`) | `/docs/services/identite/keycloak/securiser-application-oidc/` |
| Compétence (provisoire) | `iam.sso.integrate` |
| Durée visée | ~45 min (à **mesurer** en jouant le lab) |
| Prérequis | lab 2 |
| Environnement | VM (`runtime.type: vm`), socle du README |

## Objectif

Déléguer la connexion de l'application témoin à Keycloak, en flux code d'autorisation avec PKCE, sans URI de redirection trop large.

## Ce que l'apprenant fait

- crée un client public pour l'application témoin
- règle l'URI de redirection exacte et les origines web
- exige PKCE (S256)
- configure l'application témoin (issuer, client_id) et se connecte

## État vérifié par les tests

- le client existe, public, flux standard seul (implicite et mot de passe désactivés)
- PKCE S256 exigé
- aucune URI de redirection en joker
- l'application témoin affiche l'utilisateur connecté et valide l'ID token (signature, `iss`, `aud`, `exp`, `nonce`)

## Cas d'échec à prévoir dans les tests

- URI de redirection `*`
- flux implicite activé
- application qui accepte un jeton d'un autre realm

## Indices (`hints.yaml`)

- l'endpoint Discovery donne l'issuer exact à copier

## À vérifier avant d'écrire

- nom du réglage PKCE dans la console de la version retenue
