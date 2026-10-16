# Challenge : un fournisseur d'identité qu'on laisse en production

Vous travaillez dans `/opt/keycloak-lab`, sur la machine `idp.lab`. Le fichier
`identifiants.txt` y porte le compte d'administration que vous devez créer, et
`LISEZ-MOI.txt` rappelle où écrire.

## Ce qui est attendu

Keycloak doit tourner, adossé à PostgreSQL, et rendre quatre choses :

1. son **point de santé** doit répondre et se déclarer prêt ;
2. la base réellement en service doit être **PostgreSQL**, et non celle que
   Keycloak embarque pour le développement ;
3. un realm nommé **`formation`** doit exister et servir sa découverte OIDC ;
4. le compte nominatif de `identifiants.txt` doit **administrer le serveur**,
   et le compte de démarrage `temp-admin` ne doit plus servir, qu'il soit
   supprimé ou désactivé.

## Ce qui est éprouvé, et comment

Les tests n'ouvrent pas votre fichier Compose : ils interrogent le serveur.
Vous arrivez au résultat par le chemin que vous voulez, pourvu que le serveur
rende ce qui est demandé.

Le dernier test **redémarre vos conteneurs** et vérifie que le realm est
toujours là. C'est la seule façon de distinguer une base qui persiste d'une
base qui fait illusion jusqu'au premier arrêt.

## Contraintes

- Le fichier Compose s'appelle `compose.yaml` et vit dans `/opt/keycloak-lab`.
  Le reste vous appartient : noms des services, des volumes, du réseau.
- Les deux ports que les tests interrogent sont ceux que Keycloak expose par
  défaut pour son application et pour sa gestion. À vous de les publier.
- Ne changez pas les valeurs de `identifiants.txt` : les tests s'authentifient
  avec.

## Deux pièges qui ont coûté des heures à d'autres

Un serveur qui répond n'est pas un serveur qui persiste. La commande de
démarrage décide de la base utilisée, et elle peut contredire ce que vous avez
déclaré dans l'environnement.

L'administrateur d'un **serveur** Keycloak ne vit pas dans le realm
applicatif. Un compte créé au bon endroit avec les bons droits administre ce
qu'il faut ; créé ailleurs, il n'administre que son propre realm.

```bash
dsoxlab check iam-02-keycloak-installer   # valide
dsoxlab hint  iam-02-keycloak-installer   # un indice, au prix de points
```
