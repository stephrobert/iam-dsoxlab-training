# iam-12-depanner-integration : Dépanner une intégration OIDC qui échoue

| Champ | Valeur |
|---|---|
| Leçon d'accueil (`doc_url`) | `/docs/services/identite/keycloak/depanner-integration/` |
| Compétence (provisoire) | `iam.sso.integrate` |
| Durée visée | ~40 min (à **mesurer** en jouant le lab) |
| Prérequis | lab 4 |
| Environnement | VM (`runtime.type: vm`), socle du README |

## Objectif

Remettre en service une application témoin dont la connexion échoue, en lisant les erreurs de l'IdP et le contenu des jetons.

## Ce que l'apprenant fait

- reçoit une application cassée par le setup (URI de redirection, horloge, issuer, audience : une panne par variante)
- lit les journaux d'événements de Keycloak et décode le jeton
- corrige la cause, pas le symptôme

## État vérifié par les tests

- l'application témoin se reconnecte
- la correction porte sur la cause injectée (vérifiée par variante)
- aucun contournement (validation de jeton désactivée, URI en joker)

## Cas d'échec à prévoir dans les tests

- validation du jeton désactivée pour « faire marcher »
- URI de redirection élargie en joker

## Indices (`hints.yaml`)

- l'erreur affichée par Keycloak nomme souvent le paramètre fautif

## À vérifier avant d'écrire

- messages d'erreur exacts de la version retenue pour chaque panne injectée
