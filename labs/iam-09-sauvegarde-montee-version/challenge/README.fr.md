# Challenge : sauvegarder, monter de version, et le prouver

`/opt/iam-lab/identifiants-lab.txt` nomme l'URL de l'instance, son répertoire,
son fichier d'environnement, les noms des deux conteneurs, le realm, le mot de
passe des comptes, les versions de départ et cible, l'image cible exacte, et
les deux répertoires où votre sauvegarde et votre export sont attendus.

L'instance tourne **sur ses propres ports** (`8081` et `9001`) : le socle, sur
`8080`, appartient aux autres labs et ne doit pas bouger.

## Ce qui est attendu

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

## Ce que la notation vérifie vraiment de votre sauvegarde

Elle ne regarde pas le nom du fichier ni sa taille seule. Elle **crée une base,
y restaure votre sauvegarde, compte les comptes, puis la supprime**. Un fichier
qui ne se restaure pas n'est pas une sauvegarde, et c'est le seul contrôle qui
fait la différence.

Elle compare aussi l'horodatage de votre sauvegarde à la **date de création du
conteneur de la version cible**. Une sauvegarde prise après échoue, et elle
échoue exprès : elle décrit un état dont vous n'avez plus besoin et ne permet
pas de retrouver celui dont vous pourriez avoir besoin.

## Quatre choses mesurées sur cette machine

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

## Une chose à savoir sur la montée elle-même

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
