# iam-09-sauvegarde-montee-version : Sauvegarder Keycloak et le mettre à jour

| Champ | Valeur |
|---|---|
| Leçon d'accueil (`doc_url`) | `(leçon à écrire) « Keycloak en production »` |
| Compétence (provisoire) | `iam.idp.operate` |
| Durée visée | ~60 min (à **mesurer** en jouant le lab) |
| Prérequis | lab 2 |
| Environnement | VM (`runtime.type: vm`), socle du README |

## Objectif

Sauvegarder ce qui doit l'être, monter de version, et prouver que rien n'est perdu.

## Ce que l'apprenant fait

- sauvegarde la base PostgreSQL et exporte le realm
- monte Keycloak d'une version à la suivante en changeant l'image épinglée
- vérifie realm, utilisateurs et clients après la montée

## État vérifié par les tests

- une sauvegarde de la base existe et se restaure dans une base vide
- Keycloak tourne dans la version cible
- realm, utilisateurs et clients sont intacts
- un utilisateur se connecte après la montée

## Cas d'échec à prévoir dans les tests

- montée sans sauvegarde
- export du realm pris pour une sauvegarde complète (il ne porte pas tout)

## Indices (`hints.yaml`)

- lire les notes de migration de la version cible avant de changer l'image

## À vérifier avant d'écrire

- couple de versions source et cible au moment d'écrire, et notes de migration correspondantes
