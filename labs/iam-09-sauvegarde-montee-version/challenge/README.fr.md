# La sauvegarde que personne n'a jamais restaurée

## La situation

La montée de version est prévue jeudi soir. Le fournisseur a deux versions
mineures de retard, l'une porte un correctif dont quelqu'un a besoin, et la
demande de changement dit, sous la rubrique « plan de retour arrière », les mots
« restaurer depuis la sauvegarde ».

Il existe une sauvegarde. Elle tourne chaque nuit, elle n'a jamais échoué, et
personne ne l'a jamais restaurée. Ces deux faits sont d'ordinaire énoncés comme
une seule phrase rassurante, et ce ne sont pas du tout le même fait. Une
sauvegarde qu'on n'a jamais restaurée est un fichier dont personne n'a vérifié
le contenu, produit par une commande dont personne ne lit le code de retour, au
sujet d'une base dont la forme a changé deux fois depuis que le script a été
écrit.

Il existe aussi un export. Quelqu'un a exporté le realm le mois dernier, avant
un changement de configuration, et a gardé le fichier. Il dort dans un
répertoire partagé nommé `sauvegardes`, et c'est quatre cents kilo-octets de
JSON qui a l'air complet, avec le realm, les clients, les flux
d'authentification et les clefs, tout y est.

Ce n'est pas une sauvegarde, et la façon dont ce n'en est pas une vaut votre
après-midi. Le fichier que quelqu'un a gardé est l'un des deux que la commande
d'export produit, et c'est celui qui ne contient aucun compte. Restaurez depuis
lui vendredi matin et vous aurez un realm avec tous ses réglages en place, tous
ses clients configurés, et personne qui puisse se connecter.

Ce qu'il ne contient pas non plus, quel que soit le fichier que vous gardez,
c'est la trace de qui s'est connecté et quand. Cette trace vit dans la base,
dans des tables que l'export ne regarde pas. Perdez-la dans une montée de
version et la question « qui avait accès en mars » cesse d'avoir une réponse,
définitivement.

Donc : une instance tourne, avec une version de retard, des comptes, des
clients et quelques jours de trace d'audit. Sauvegardez-la correctement,
montez-la de version, puis prouvez que rien n'est perdu, ce qui veut dire le
prouver pour la trace autant que pour les comptes.

L'ordre compte, et c'est la seule partie de ce lab qu'on ne peut pas rattraper
après.

## Sauvegarder, monter de version, et le prouver

`/opt/iam-lab/identifiants-lab.txt` nomme l'URL de l'instance, son répertoire,
son fichier d'environnement, les noms des deux conteneurs, le realm, le mot de
passe des comptes, les versions de départ et cible, l'image cible exacte, et
les deux répertoires où votre sauvegarde et votre export sont attendus.

L'instance tourne **sur ses propres ports** (`8081` et `9001`) : le socle, sur
`8080`, appartient aux autres labs et ne doit pas bouger.

### Ce qui est attendu

1. Une **sauvegarde de la base** dans `REPERTOIRE_SAUVEGARDES`, prise **avant**
   la montée, et qui **se restaure dans une base vide** avec les comptes
   dedans.
2. Un **export du realm** dans `REPERTOIRE_EXPORTS`, assez complet pour que les
   comptes y soient quelque part.
3. L'instance en `VERSION_CIBLE`, avec l'image **épinglée par digest** dans le
   fichier d'environnement, et non seulement changée à l'exécution.
4. Le realm, les comptes et les clients intacts.
5. La **trace d'audit** toujours dans la base.
6. Un compte qui se connecte encore.

### Ce que la notation vérifie vraiment de votre sauvegarde

Elle ne regarde pas le nom du fichier ni sa taille seule. Elle **crée une base,
y restaure votre sauvegarde, compte les comptes, puis la supprime**. Un fichier
qui ne se restaure pas n'est pas une sauvegarde, et c'est le seul contrôle qui
fait la différence.

Elle compare aussi l'horodatage de votre sauvegarde à la **date de création du
conteneur de la version cible**. Une sauvegarde prise après échoue, et elle
échoue exprès : elle décrit un état dont vous n'avez plus besoin et ne permet
pas de retrouver celui dont vous pourriez avoir besoin.

### Quatre choses mesurées sur cette machine

**`kc.sh export` lancé dans le conteneur en marche sort en 1** sur « Unable to
start the management interface on 0.0.0.0:9000: Address already in use », **et
écrit quand même les fichiers**. Lisez le code de retour et vous croyez à un
échec ; listez le répertoire et vous croyez au succès. Lancez-le plutôt dans un
conteneur jetable (`docker compose run --rm --no-deps`) et il sort en 0.

**L'export écrit deux fichiers, et `<realm>-realm.json` ne porte aucun
compte.** `has("users")` y vaut `false`. Les comptes sont dans
`<realm>-users-0.json`. C'est le piège du scénario, et il est réel.

**Ce fichier de comptes porte les `credentials` avec leur `secretData`.** C'est
un fichier de secrets. Donnez-lui les droits qui vont avec.

**L'export ne contient aucun événement.** Les seules clefs qui parlent
d'événements y sont de la configuration (`eventsEnabled`, `enabledEventTypes`),
pas les événements. La trace vit dans `event_entity` et `admin_event_entity`,
dans la base, et c'est la raison pour laquelle un export n'est pas une
sauvegarde.

### Une chose à savoir sur la montée elle-même

Le schéma migre automatiquement au démarrage, et le dit dans les journaux. Cela
vaut d'être su avant de changer l'image : les notes de migration de la 26.8
indiquent qu'au-delà de 300000 lignes dans `OFFLINE_USER_SESSION`, la migration
automatique **saute** la création d'un index et la journalise pour application à
la main. Un service qui redémarre « sans erreur » peut donc avoir un index en
moins. Cette instance est bien trop petite pour que cela arrive ici, et
l'habitude de lire les notes de migration d'abord est tout le propos.

```bash
dsoxlab check iam-09-sauvegarde-montee-version   # noter
dsoxlab hint  iam-09-sauvegarde-montee-version   # un indice, au prix de quelques points
```
