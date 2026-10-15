# Exposer un Deployment par un Service ClusterIP

## La situation

Dans le namespace **`lab`**, l'équipe veut un serveur web en **trois
replicas**, joignable par les autres applications du cluster sous un nom
stable, **`web-svc`**, quel que soit le Pod qui répond. Pour vérifier la
répartition, chaque Pod doit répondre avec **son propre nom**.

Un Pod **`client`** est là pour interroger le Service.

## Ce que vous devez obtenir

1. Un Deployment **`web`** dans `lab`, trois replicas, image `busybox:1.36`,
   dont chaque Pod sert son nom d'hôte en HTTP sur le port **8080**. Ses
   Pods portent le label `app=web`.

2. Un Service **`web-svc`** de type ClusterIP, port **80**, qui vise le port
   8080 des Pods `app=web`.

3. Depuis `client`, `http://web-svc/` répond, et sur une dizaine de
   requêtes, **au moins deux Pods différents** répondent.

## Les repères utiles

Un serveur qui répond son nom d'hôte tient en une commande busybox :
`hostname` dans un fichier, puis `httpd -f` sur ce répertoire. Dans un Pod,
le nom d'hôte est le nom du Pod.

`kubectl expose deployment` crée le Service en une commande, si on lui dit
le port et le port cible.

## Comment vous saurez que c'est bon

Les tests lisent le Deployment et le Service, puis font dix requêtes depuis
`client` et comptent les Pods qui ont répondu.

```bash
dsoxlab check ckad-expose-service
```
