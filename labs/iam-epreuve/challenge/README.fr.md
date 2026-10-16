# Épreuve finale : huit tâches, deux heures, aucun indice

Lisez d'abord `/opt/iam-lab/identifiants-lab.txt`. C'est le cahier des charges,
et il vous dit quel compte joue quel rôle dans cette épreuve.

## 1. Un fournisseur qui dure

Répondant sur l'URL donnée, la santé sur le port de gestion, les données qui
survivent à un redémarrage, un administrateur **nominatif**, aucun compte de
démarrage laissé derrière. Le realm nommé dans le cahier des charges doit
exister.

## 2. L'annuaire, fédéré

Ses comptes utilisables à travers le fournisseur, l'un d'eux se connectant. Ses
groupes arrivant **avec leurs membres**. En lecture seule : le fournisseur
n'écrit pas dans l'annuaire.

## 3. L'application, branchée

OIDC, flux de code, PKCE S256, implicite et octroi direct fermés, URI de
redirection exactes. Puis configurez et démarrez le témoin pour qu'un parcours
complet fonctionne et affiche le nom de la personne.

## 4. L'API, fermée

Signature, issuer, audience, expiration. Puis le scope : **403** quand le jeton
est valide mais insuffisant, **401** quand il est absent ou invalide. Un client
machine lit et n'écrit pas.

## 5. Un second facteur, pour le seul groupe sensible

Imposé **par le groupe**, pour qu'il suive l'appartenance plutôt qu'une liste de
noms. Le compte nommé `COMPTE_CONCERNE` doit être arrêté par lui ; celui nommé
`COMPTE_EPARGNE` doit entrer.

Prenez garde à la condition qui n'exige un facteur que de ceux qui en ont déjà
un : avec elle en place, l'étape peut être obligatoire sans que personne ne soit
réellement obligé à quoi que ce soit.

Laissez intact le flux de navigateur fourni. Travaillez sur une copie, et
activez la copie.

## 6. Une politique de mot de passe qui tient

La longueur d'abord. Aucune règle de composition, aucune expiration forcée :
les deux produisent des mots de passe prévisibles écrits sur un papier.

## 7. Le départ, terminé

`QUI_PART` doit finir **désactivé**, **sans aucun groupe** et **sans aucune
session**.

Deux de ces trois gestes rapportent un succès sans rien faire, et l'un d'eux est
refusé par le fournisseur lui-même. Contrôlez l'état après chacun plutôt que
leur code de retour.

## 8. Une revue, et une sauvegarde

La revue liste tous les comptes avec leurs groupes **et leurs rôles**, et elle
décrit l'état **après** le départ, pas avant.

La sauvegarde est celle de la **base**, et l'épreuve la restaure dans une base
qu'elle crée pour l'occasion. Un export du realm ne passera pas : il ne porte
aucun événement, donc aucune trace de qui s'est connecté.

## Comment vous êtes jugé

Seize contrôles sur l'état du système, listés dans le `README` de ce lab. Le
seuil de réussite est de 75 pour cent du barème.

```bash
dsoxlab check iam-epreuve
dsoxlab submit iam-epreuve
```
