# Challenge : une seule source de vérité, en lecture seule

L'annuaire et le fournisseur tournent tous deux sur `idp.lab`, dans des
conteneurs. `/opt/iam-lab/identifiants-lab.txt` porte le DN de base, les deux
branches, le compte de liaison, et le mot de passe des trois comptes de
l'annuaire.

L'annuaire contient déjà ce que le premier lab demande de créer : `aline`,
`bruno` et `chloé`, dans les groupes `devops` et `lecteurs`. Le fournisseur ne
connaît personne.

## Ce qui est attendu

1. Une **fédération d'utilisateurs** de type LDAP dans le realm `formation`,
   activée, avec l'**import actif** et en mode **lecture seule**.
2. Elle pointe sur la branche des personnes de l'annuaire, et lit `uid` comme
   nom d'utilisateur.
3. Un **mappeur de groupes** sur cette fédération, qui pointe sur la branche
   des groupes et lit l'appartenance dans l'attribut que l'annuaire publie.
4. Les **deux synchronisations** ont été lancées : les comptes, puis les
   groupes. Déclarer n'importe pas.
5. `aline` obtient un jeton sur le realm avec le mot de passe de
   `identifiants-lab.txt`.

## Ce qui est prouvé, et comment

Les tests ne lisent pas votre configuration pour la juger bonne. Ils regardent
ce que le fournisseur **connaît** et ce qu'il **refuse** :

- les trois personnes sont connues du realm, chacune rattachée à la fédération,
  chacune avec son adresse ;
- `devops` contient exactement `aline` et `bruno`, `lecteurs` exactement
  `bruno` et `chloe` ;
- `aline` obtient un jeton ;
- une demande de changement du prénom d'un compte fédéré est **refusée**, avec
  `error-user-attribute-read-only`.

Le dernier est celui qu'on ne peut pas simuler. Un mode posé sans effet
ressemble exactement à un mode posé correctement, jusqu'au jour où quelqu'un
corrige un nom.

## Contraintes

- Le realm est `formation`. Une fédération, pas deux : à deux, la priorité
  décide de qui répond et le résultat cesse d'être prévisible.
- L'annuaire publie l'appartenance dans `member` côté groupe, et aussi dans
  `uniqueMember` et `memberOf`.
- Les comptes portent `inetOrgPerson`, et leur identifiant est `uid`.
- Ne changez rien dans l'annuaire : c'est la source, désormais.

## Le piège, dit sans détour, parce qu'il coûte une après-midi

Keycloak tourne dans un conteneur. Dans ce conteneur, `127.0.0.1` est le
conteneur lui-même, pas la machine. Mesuré depuis lui : `127.0.0.1:3890` est
**fermé**, `lldap:3890` est **ouvert**.

Avec la mauvaise adresse, tout a l'air juste. La fédération est créée, elle est
activée, et la synchronisation répond HTTP `200` avec
`0 imported users, 0 updated users`. Aucune erreur, aucun avertissement. Lisez
le nombre que la synchronisation vous rend, chaque fois.

À propos d'`entryUUID` : l'annuaire donne à chaque entrée un identifiant stable
qui survit à un renommage, là où son DN ne survit pas. Dire à la fédération de
s'en servir, c'est ce qui garde un compte renommé rattaché à ses sessions au
lieu de le faire arriver comme une nouvelle personne.

```bash
dsoxlab check iam-03-federation-ldap   # noter
dsoxlab hint  iam-03-federation-ldap   # un indice, au prix de quelques points
```
