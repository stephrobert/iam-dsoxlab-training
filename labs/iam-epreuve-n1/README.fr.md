# Comment cette épreuve fonctionne

Ce n'est pas un tutoriel, et il n'y a pas de `hints.yaml`. Rien ici ne vous dit
comment faire le travail : c'est à cela que servaient les quatre labs qui
précèdent.

Ce que cette page fait, c'est vous dire comment vous êtes jugé, pour qu'aucune
part de votre note ne vous surprenne.

## Ce qui est mesuré

L'**état du système**, lu par l'API du fournisseur lui-même, par les points
d'état des témoins, et par l'état des conteneurs. Dix contrôles :

| # | Ce qu'il lit |
|---|---|
| 1 | Le fournisseur répond, son port de gestion est sain, un compte d'administration **nominatif** existe, et aucun compte de démarrage ne subsiste |
| 2 | Le fournisseur **survit à un redémarrage** avec ses données : le test pose une marque, redémarre le conteneur, et relit la marque |
| 3 | Les trois comptes de l'annuaire sont connus du realm, et l'un d'eux s'y connecte |
| 4 | Le groupe de l'annuaire porte **ses membres**, et pas seulement son nom |
| 5 | Le client de l'application est public, en flux de code, PKCE S256, avec implicite et octroi direct **fermés** et aucune redirection à joker |
| 6 | Un **parcours de connexion complet** va de l'application au fournisseur et revient, et l'application affiche le nom de la personne |
| 7 | L'API répond **401 sans jeton** et 200 avec le bon |
| 8 | L'API répond **403** sur une écriture tentée avec un jeton de lecture |
| 9 | L'API **refuse un jeton émis pour une autre application** |
| 10 | Un client machine lit l'API et **ne peut pas y écrire** |

La façon d'y arriver n'est pas mesurée. Console, appels d'API, script, un
mélange : cela ne change rien. Deux de ces contrôles modifient l'état pendant
qu'ils tournent (le redémarrage, et la marque qu'il pose) et tous deux
remettent les choses comme elles étaient.

## Ce que le cahier des charges vous donne

`/opt/iam-lab/identifiants-lab.txt` nomme le realm, le compte d'administration
à créer et son mot de passe, les URL et les ports attendus, les DN de
l'annuaire et son justificatif d'administration, les comptes et leur mot de
passe commun, tous les identifiants de clients, tous les scopes, et les
répertoires et ports des deux témoins.

Rien n'est caché. Une épreuve qui vous ferait deviner des noms mesurerait de la
devinette.

## Ce dont vous partez

- Docker, Compose et les outils, installés.
- Un **annuaire peuplé**, à l'écoute sur la machine, avec trois comptes et deux
  groupes. Le monter est le lab 01, hors du périmètre de cette épreuve.
- Une **application témoin** qui ne connaît aucun fournisseur, et une **API
  témoin qui répond à tout le monde**. Les deux sont à brancher.
- **Aucun fournisseur d'identité.** En installer un est la première chose
  demandée.

## Une chose à savoir avant de commencer

L'annuaire vit dans son propre projet Compose, et le fournisseur que vous
installerez vivra dans un autre. Docker résout les noms à l'intérieur d'un
réseau, pas entre deux.

L'annuaire publie donc son port LDAP sur la machine, et le cahier des charges
vous donne l'adresse de la machine.

Ne tendez pas la main vers `127.0.0.1` depuis le conteneur du fournisseur.
De là, `127.0.0.1` est le conteneur.

```bash
dsoxlab check iam-epreuve-n1    # noter
dsoxlab submit iam-epreuve-n1   # noter et consigner le verdict
```
