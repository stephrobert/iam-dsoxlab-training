# Challenge : un cluster et un outil qui font confiance au fournisseur

`/opt/iam-lab/identifiants-lab.txt` nomme tout ce que les tests cherchent : le
nom du cluster, le namespace, les deux groupes et leur compte, les
identifiants de clients, l'audience, les deux issuers, le chemin du CA,
l'emplacement attendu de la configuration d'authentification, et le fichier
d'environnement de l'outil.

Le setup a installé `k3d` et `kubectl`, tiré l'image du cluster, posé un
**accès TLS devant le fournisseur**, créé deux groupes avec un compte chacun,
et démarré l'outil **sans** aucune connaissance du fournisseur. Il n'y a pas
encore de cluster. Le créer vous revient.

## Ce qui est attendu

1. Un cluster nommé comme le dit `CLUSTER_ATTENDU`, dont le serveur d'API lit
   une **configuration d'authentification**.
2. Cette configuration nomme l'**issuer TLS**, exige l'audience, et porte le CA
   du fournisseur.
3. Un client `kubernetes` : public, PKCE `S256`, avec un **mappeur d'audience**
   et un **mappeur de groupes**.
4. Un jeton pris par la porte TLS authentifie le compte **avec son groupe** ;
   un jeton pris par la porte HTTP est **refusé**.
5. `devops` écrit dans le namespace `applications` et **nulle part ailleurs** ;
   `lecteurs` lit partout et n'écrit rien ; **aucun groupe n'est lié à
   `cluster-admin`**.
6. L'outil laisse entrer le compte **par le fournisseur**, jusqu'à une session.

## Ce qui coûte une après-midi, mesuré sur cette machine

**En Kubernetes 1.37, les drapeaux `--oidc-*` ont disparu.** Seule reste la
configuration structurée, `apiVersion: apiserver.config.k8s.io/v1beta1`, passée
par `--authentication-config`. Tous les tutoriels écrits avant la 1.29 montrent
des drapeaux qui n'existent plus.

**Elle refuse un issuer en http**, et elle refuse en **ne démarrant pas** :

```text
Error: invalid authentication configuration: jwt[0].issuer.url:
Invalid value: "http://...": URL scheme must be https
```

Ce que vous voyez, à la place, c'est `k3d` qui abandonne sur un délai dépassé
en disant que le nœud n'est pas devenu prêt. La raison est dans
`docker logs k3d-<cluster>-server-0`, et `k3d` supprime ce conteneur en
annulant sa création : passez `--no-rollback` quand vous voulez la lire.

**Le fournisseur répond sur deux portes et ne se décrit pas pareil sur
chacune.** Il calcule son issuer depuis la requête. Demandez
`.well-known/openid-configuration` sur chaque porte et comparez, avant
d'écrire quoi que ce soit dans la configuration du cluster.

**Le serveur d'API doit résoudre le nom de l'issuer depuis son conteneur.**
`k3d` a une option pour cela, et sans elle vous obtenez une configuration juste
qui ne peut pas aller chercher les clefs du fournisseur.

**`kubectl --token` est ignoré quand le kubeconfig courant porte un certificat
client.** `auth whoami` répond alors `system:admin` avec `system:masters`, et
vous concluez que votre OIDC fonctionne alors que vous venez de mesurer votre
propre certificat d'administration. Éprouvez un jeton avec un kubeconfig vide.
Celui-là vaut d'être retenu bien au-delà de ce lab.

## Deux cas d'échec que la notation attrape

**Un groupe lié à `cluster-admin`.** Cela marche, c'est une commande, et cela
donne la machine à quiconque parvient à rejoindre un groupe dans un annuaire
que vous n'administrez pas.

**Un jeton sans le claim des groupes.** Le compte s'authentifie, ne porte que
`system:authenticated`, et se voit refusé bien que la liaison RBAC existe. Cela
ressemble exactement à un RBAC cassé, et ce n'en est pas un : demandez le claim
sur le client.

```bash
dsoxlab check iam-14-plateforme   # noter
dsoxlab hint  iam-14-plateforme   # un indice, au prix de quelques points
```
