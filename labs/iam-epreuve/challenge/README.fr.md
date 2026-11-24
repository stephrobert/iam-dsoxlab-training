# Tout, sur une machine, avant la fin de la journée

## La situation

L'audit est dans trois semaines. L'auditeur a envoyé sa liste de questions en
avance, ce qui est une politesse, et la liste est assez courte pour se lire en
une minute et assez longue pour expliquer pourquoi personne ne dort bien depuis.

Qui peut se connecter. Où vivent leurs comptes. Ce qui se passe quand quelqu'un
part. Si quelqu'un a un second facteur. Si vous pouvez prouver quoi que ce soit
de tout cela.

Pour l'instant les réponses honnêtes sont : personne ne sait, à quatre endroits,
rien, non, et non.

Vous avez une machine, un annuaire avec trois personnes dedans, une application
qui n'a pas de page de connexion, et une API qui répond à qui demande. Vous avez
jusqu'à la fin de la journée.

Ce que l'auditeur vérifiera n'est pas votre configuration. C'est si l'état du
système correspond à ce que vous lui avez dit. C'est donc ce que cette épreuve
vérifie aussi : seize lectures du système, dont aucune ne se soucie de la façon
dont vous y êtes arrivé.

Quatre de ces lectures méritent d'y penser avant de commencer.

**Le fournisseur doit survivre à un redémarrage.** Non parce que les
redémarrages sont fréquents, mais parce qu'un fournisseur qui perd son realm au
redémarrage n'a pas de realm : il a une démonstration.

**Le second facteur va au groupe sensible, et à lui seul.** Imposé à tout le
monde, il enferme l'administrateur dehors, et le remède habituel à ce moment-là
est de tout désactiver le lundi matin. Imposé à personne, ce qui arrive plus
souvent, il passe toutes les inspections visuelles : l'étape est là, elle est
obligatoire, et les gens qui n'ont aucun second facteur entrent directement.

**Le départ doit être terminé.** Trois gestes, et deux d'entre eux répondent
« fait » sans avoir rien fait. L'un d'eux est refusé par le fournisseur
lui-même, poliment, d'une façon qu'il faut aller chercher.

**La sauvegarde doit se restaurer.** Pas exister : se restaurer. Cette épreuve
crée une base, y met votre sauvegarde, et compte ce qui est revenu. Un export
du realm ne passera pas, et il ne passera pas pour une raison qui intéresse
l'auditeur : il ne contient aucune trace de qui s'est connecté.

Le cahier des charges est dans `/opt/iam-lab/identifiants-lab.txt`. Il nomme les
trois comptes et le rôle que chacun joue dans cette épreuve, et cette partie
mérite d'être lue attentivement : l'un des trois ne doit pas être dans le groupe
sensible, et le cahier des charges vous dit lequel.

Il n'y a aucun indice.

## Épreuve finale : huit tâches, deux heures, aucun indice

Lisez d'abord `/opt/iam-lab/identifiants-lab.txt`. C'est le cahier des charges,
et il vous dit quel compte joue quel rôle dans cette épreuve.

### 1. Un fournisseur qui dure

Répondant sur l'URL donnée, la santé sur le port de gestion, les données qui
survivent à un redémarrage, un administrateur **nominatif**, aucun compte de
démarrage laissé derrière. Le realm nommé dans le cahier des charges doit
exister.

### 2. L'annuaire, fédéré

Ses comptes utilisables à travers le fournisseur, l'un d'eux se connectant. Ses
groupes arrivant **avec leurs membres**. En lecture seule : le fournisseur
n'écrit pas dans l'annuaire.

### 3. L'application, branchée

OIDC, flux de code, PKCE S256, implicite et octroi direct fermés, URI de
redirection exactes. Puis configurez et démarrez le témoin pour qu'un parcours
complet fonctionne et affiche le nom de la personne.

### 4. L'API, fermée

Signature, issuer, audience, expiration. Puis le scope : **403** quand le jeton
est valide mais insuffisant, **401** quand il est absent ou invalide. Un client
machine lit et n'écrit pas.

### 5. Un second facteur, pour le seul groupe sensible

Imposé **par le groupe**, pour qu'il suive l'appartenance plutôt qu'une liste de
noms. Le compte nommé `COMPTE_CONCERNE` doit être arrêté par lui ; celui nommé
`COMPTE_EPARGNE` doit entrer.

Prenez garde à la condition qui n'exige un facteur que de ceux qui en ont déjà
un : avec elle en place, l'étape peut être obligatoire sans que personne ne soit
réellement obligé à quoi que ce soit.

Laissez intact le flux de navigateur fourni. Travaillez sur une copie, et
activez la copie.

### 6. Une politique de mot de passe qui tient

La longueur d'abord. Aucune règle de composition, aucune expiration forcée :
les deux produisent des mots de passe prévisibles écrits sur un papier.

### 7. Le départ, terminé

`QUI_PART` doit finir **désactivé**, **sans aucun groupe** et **sans aucune
session**.

Deux de ces trois gestes rapportent un succès sans rien faire, et l'un d'eux est
refusé par le fournisseur lui-même. Contrôlez l'état après chacun plutôt que
leur code de retour.

### 8. Une revue, et une sauvegarde

La revue liste tous les comptes avec leurs groupes **et leurs rôles**, et elle
décrit l'état **après** le départ, pas avant.

La sauvegarde est celle de la **base**, et l'épreuve la restaure dans une base
qu'elle crée pour l'occasion. Un export du realm ne passera pas : il ne porte
aucun événement, donc aucune trace de qui s'est connecté.

### Comment vous êtes jugé

Seize contrôles sur l'état du système, listés dans le `README` de ce lab. Le
seuil de réussite est de 75 pour cent du barème.

```bash
dsoxlab check iam-epreuve
dsoxlab submit iam-epreuve
```
