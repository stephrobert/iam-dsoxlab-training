# Comment cette épreuve fonctionne

Ce n'est pas un tutoriel, et il n'y a pas de `hints.yaml`. Rien ici ne vous dit
comment faire le travail : les labs l'ont fait.

Ce que cette page vous dit, c'est comment vous êtes jugé.

## Les seize contrôles

Tous lisent l'**état du système** : l'API du fournisseur, les points d'état des
témoins, l'état des conteneurs, la base elle-même.

| # | Ce qu'il lit |
|---|---|
| 1 | Le fournisseur répond, port de gestion sain, administrateur **nominatif**, aucun compte de démarrage |
| 2 | Le fournisseur **survit à un redémarrage** avec ses données |
| 3 | Les comptes de l'annuaire sont connus du realm, et l'un s'y connecte |
| 4 | Le groupe de l'annuaire porte **ses membres** |
| 5 | Le client de l'application : public, flux de code, PKCE S256, implicite et octroi direct fermés, aucun joker |
| 6 | Un **parcours complet** fonctionne et affiche le nom de la personne |
| 7 | L'API répond **401** sans jeton, 200 avec le bon |
| 8 | L'API répond **403** sur une écriture avec un jeton de lecture |
| 9 | L'API **refuse un jeton émis pour une autre application** |
| 10 | Un client machine lit l'API et **ne peut pas écrire** |
| 11 | Le second facteur est imposé **par le groupe**, avec une condition de rôle configurée, et `conditional-user-configured` retirée |
| 12 | Deux parcours se terminent **différemment** : le compte concerné est arrêté, l'épargné entre |
| 13 | La politique de mot de passe mise sur la **longueur**, sans règle de composition ni expiration |
| 14 | Le départ est terminé : **désactivé, sans groupe, sans session** |
| 15 | La revue des accès est **complète et à jour**, avec les rôles autant que les groupes |
| 16 | Une sauvegarde de la base **se restaure dans une base vide**, avec les comptes dedans |

Plusieurs de ces contrôles modifient l'état pendant qu'ils tournent : le
redémarrage du 2, les parcours du 12, la base jetable du 16. Tous remettent les
choses en place.

## Lisez le cahier des charges attentivement

`/opt/iam-lab/identifiants-lab.txt` nomme tout, et il nomme une chose dont vous
avez besoin avant de commencer : **lequel des trois comptes joue quel rôle**.

- `UTILISATEUR` joue le parcours de connexion et utilise l'API. Il n'est
  **pas** dans le groupe sensible, et c'est délibéré : le second facteur que
  vous allez imposer arrêterait sinon son parcours, et le contrôle 6
  échouerait sur l'exigence même que le contrôle 11 vous demande de poser.
- `COMPTE_CONCERNE` est dans le groupe sensible, et doit être arrêté par le
  second facteur.
- `COMPTE_EPARGNE` doit entrer sans en avoir.
- `QUI_PART` est le départ.

## Ce dont vous partez

Docker et les outils. Un annuaire peuplé sur la machine, dans son propre projet
Compose. Une application témoin qui ne sait rien, et une API témoin qui répond à
tout le monde. **Aucun fournisseur d'identité.** Aucune sauvegarde. Aucune
revue.

## Deux choses qui coûtent une après-midi chacune

L'annuaire et le fournisseur vivent dans des **projets Compose différents**,
donc aucun nom ne se résout entre les deux. L'annuaire publie son port LDAP sur
la machine, et depuis le conteneur du fournisseur, `127.0.0.1` est le conteneur.

Une appartenance fédérée **ne peut pas être retirée depuis le fournisseur**
quand le mappeur est en lecture seule. Elle se retire à la source, se
resynchronise, et le cache des comptes fédérés du fournisseur doit ensuite être
vidé, ce qui est un appel à part que rien ne vous indique.

```bash
dsoxlab check iam-epreuve    # noter
dsoxlab submit iam-epreuve   # noter et consigner le verdict
```
