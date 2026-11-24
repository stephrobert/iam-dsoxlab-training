# Lundi matin, et rien n'est branché

## La situation

L'entreprise a un annuaire. Il est là depuis des années, il porte les trois
personnes qui utiliseront ce que vous allez construire aujourd'hui, et il
fonctionne. C'est la seule chose qui fonctionne.

Il n'y a pas de fournisseur d'identité. Il y a une application qui affiche des
notes, et une API qui les sert, et les deux ont été écrites par quelqu'un qui
est parti. L'application n'a pas de page de connexion. L'API répond à qui
demande, et c'est ainsi que les notes se sont retrouvées dans un ticket de
support le mois dernier, collées par quelqu'un qui n'était pas censé les voir.

Vous avez la machine, l'annuaire, et jusqu'à la fin de la matinée.

Ce qui est attendu n'est pas une démonstration. C'est un fournisseur qui est
encore là après le redémarrage de la machine, un annuaire dont les comptes et
les groupes sont utilisables à travers lui, une application qui envoie les gens
chez le fournisseur et affiche leur nom quand ils reviennent, et une API qui
refuse ce qu'elle doit refuser.

Cette dernière est la partie que l'on rate, et on la rate d'une façon précise :
on fait vérifier à l'API que le jeton est valide. Un jeton de ce fournisseur,
pour cette personne, émis pour une application entièrement différente, est
valide. Si cela suffit à votre API, alors toutes les applications du realm
peuvent lire les notes, et vous avez reconstruit le ticket du mois dernier avec
plus d'étapes.

Il n'y a aucun indice dans cet exercice. Les tests lisent l'état du système,
donc la façon d'y arriver vous appartient : console, API, script, cela ne change
rien. Ce qui compte est ce qui est vrai à la fin.

Le cahier des charges est dans `/opt/iam-lab/identifiants-lab.txt`. Il nomme
tout ce que les tests cherchent, parce qu'une épreuve qui cacherait les noms
mesurerait de la devinette.

## Épreuve de niveau 1 : quatre tâches, quatre-vingt-dix minutes, aucun indice

Lisez d'abord `/opt/iam-lab/identifiants-lab.txt`. C'est le cahier des charges,
et tous les noms que les tests cherchent y sont.

### 1. Installer un fournisseur d'identité qui dure

Il doit répondre sur l'URL que le cahier des charges donne, exposer un point de
santé sur le port de gestion, et **garder ses données au redémarrage**. Il doit
avoir un administrateur **nominatif**, et aucun compte de démarrage laissé
derrière : un compte partagé qui administre un serveur ne laisse aucune trace
de qui a fait quoi.

Le realm nommé dans le cahier des charges doit exister.

### 2. Fédérer l'annuaire

Ses trois comptes doivent être utilisables à travers le fournisseur, et l'un
d'eux doit pouvoir se connecter. Ses groupes doivent arriver **avec leurs
membres** : un groupe au bon nom et vide est le résultat habituel, et il passe
une inspection visuelle.

Fédération en lecture seule. Le fournisseur n'écrit pas dans l'annuaire.

### 3. Brancher l'application témoin

OIDC, flux de code d'autorisation, PKCE S256. Le flux implicite fermé, l'octroi
direct fermé, URI de redirection exactes.

Puis configurez l'application témoin elle-même et démarrez-la, pour qu'un
parcours complet fonctionne : l'application envoie la personne chez le
fournisseur, le fournisseur la renvoie, et l'application affiche son nom.

### 4. Fermer l'API témoin

Pour l'instant elle répond à tout le monde. Elle doit vérifier, à chaque
requête :

- la **signature**, pour que le jeton vienne du fournisseur ;
- l'**issuer**, pour qu'il vienne du bon realm de ce fournisseur ;
- l'**audience**, pour qu'il ait été émis pour cette API ;
- l'**expiration**.

Puis le **scope**, qui est une autre question : le jeton est valide, et il peut
ne pas suffire. Un jeton de lecture employé pour une écriture obtient **403**,
et non 401. Un jeton absent ou invalide obtient **401**.

Un client machine doit pouvoir lire l'API, et ne doit pas pouvoir y écrire. En
client credentials, personne n'est là pour demander un scope : ce dont il a
besoin doit donc être attaché par défaut, et ce dont il n'a pas besoin ne doit
pas l'être.

### Comment vous êtes jugé

Dix contrôles sur l'état du système, listés dans le `README` de ce lab. Le seuil
de réussite est de 70 pour cent du barème, et `dsoxlab submit` rend le verdict.

```bash
dsoxlab check iam-epreuve-n1
dsoxlab submit iam-epreuve-n1
```
