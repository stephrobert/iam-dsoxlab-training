# Challenge : trois personnes, deux groupes, et un refus à trouver

L'annuaire tourne sur `idp.lab`. `/opt/iam-lab/identifiants-lab.txt` porte son
DN de base, le DN et le mot de passe de son administrateur, et ses deux URL.

LLDAP impose son propre arbre : `ou=people` et `ou=groups` existent déjà, et il
n'acceptera pas une unité d'organisation que vous créeriez ailleurs. Travaillez
dedans.

## Ce qui est attendu

Trois comptes sous `ou=people` :

| uid | cn | mail |
|---|---|---|
| `aline` | `Aline Dupont` | `aline@formation.lab` |
| `bruno` | `Bruno Keller` | `bruno@formation.lab` |
| `chloe` | `Chloé Nguyen` | `chloe@formation.lab` |

Deux groupes sous `ou=groups`, avec exactement ces membres :

| cn | membres |
|---|---|
| `devops` | `aline`, `bruno` |
| `lecteurs` | `bruno`, `chloe` |

Exactement ceux-là. Un groupe avec une personne de trop accorde un droit que
personne n'a demandé, et c'est ce qu'une revue d'accès déterre des mois plus
tard.

## Ce qui est prouvé, et comment

Chaque test lance `ldapsearch`, parce que c'est ce qu'un fournisseur d'identité
fera ensuite :

- chaque compte existe avec son `cn` et son `mail` ;
- chaque groupe contient exactement ses membres, lus depuis le groupe ;
- le `memberOf` de chaque compte nomme ses groupes, lus depuis le compte ;
- un filtre `(memberOf=cn=devops,…)` rend les bonnes personnes ;
- les données survivent à un `docker restart` du conteneur de l'annuaire.

Le dernier n'est pas une formalité. Un volume déclaré ne prouve pas qu'il est
monté là où les données s'écrivent, et le seul moyen de le savoir est d'arrêter
la chose.

## Contraintes

- Les noms sont imposés : les tests les cherchent.
- Ne touchez ni au compte `admin` ni aux groupes `lldap_*` : ils appartiennent
  à l'annuaire.
- Rien n'est imposé sur la *façon* d'écrire. LDIF, API, interface web : les
  tests lisent le résultat.

## Le refus qui ressemble à un succès

LLDAP est un annuaire léger, et il n'accepte pas toutes les écritures qu'un
serveur LDAP accepte d'ordinaire. L'un de ses refus est silencieux : la commande
rend un succès, et rien ne se passe.

Trouvez-le en vérifiant votre travail après chaque étape plutôt qu'à la fin.
Relisez ce que vous avez écrit, avec `ldapsearch`, avant de passer à la suite.
L'annuaire a aussi une API, et son schéma liste ce qu'elle sait faire.

Les valeurs non ASCII reviennent encodées en base64, signalées par un double
deux-points (`cn:: Q2hs…`). C'est le format LDIF, pas une erreur : décodez avant
de conclure que votre compte est mauvais.

```bash
dsoxlab check iam-01-annuaire-lldap   # noter
dsoxlab hint  iam-01-annuaire-lldap   # un indice, au prix de quelques points
```
