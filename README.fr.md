# iam-dsoxlab-training

**Langue :** [English](./README.md) · [Français](./README.fr.md)

Catalogue de labs vérifiables pour la formation
[Gestion des identités et des accès](https://blog.stephane-robert.info/docs/services/identite/)
du blog. Il est joué par la CLI [dsoxlab](https://github.com/stephrobert/dsoxlab),
qui vit ailleurs : ce dépôt n'est qu'un fournisseur de contenu.

> **État : en construction.** Le squelette du catalogue est posé, aucun lab
> n'est encore écrit. Les seize fiches qui les décrivent vivent dans
> `preparation/fiches/`. Un lab n'apparaît dans `meta.yml` que le jour où il
> est écrit **et** joué.

## Pourquoi ce dépôt existe

Une formation IAM peut s'enseigner entièrement sur le papier : des schémas de
flux, des noms de protocoles, des copies d'écran de console d'administration.
L'apprenant sort en reconnaissant le vocabulaire, sans avoir jamais vu un jeton
refusé pour la bonne raison.

Or rien, dans ce domaine, ne se prouve par la lecture. Un client OIDC mal
configuré rend un jeton qui ressemble à un jeton valide. Une API qui ne vérifie
pas l'audience accepte un jeton émis pour quelqu'un d'autre. Une déconnexion
qui ferme la session laisse l'ancien jeton d'accès valide jusqu'à son
expiration. Ces trois faits se constatent en une commande et ne s'oublient
plus ; expliqués, ils glissent.

Ce catalogue donne donc à l'apprenant de quoi **se vérifier lui-même**, sur un
vrai fournisseur d'identité, avec de vraies applications.

## La règle qui gouverne tout le reste

**Un lab est noté sur l'état du système, jamais sur les commandes tapées.**

L'apprenant arrive au résultat par le chemin qu'il veut. Les tests interrogent
donc Keycloak par son API d'administration et ses points d'accès OIDC,
l'annuaire en LDAP, et les applications témoins par leurs propres réponses.

```python
# NON : on relit ce que l'apprenant a écrit, et cela ne prouve rien
assert "pkce" in config_lue

# OUI : on demande au fournisseur ce qu'il exige vraiment
client = admin.get(f"/admin/realms/{realm}/clients/{id}")
assert client["attributes"]["pkce.code.challenge.method"] == "S256"
```

Et un lab s'éprouve **dans les deux sens** : après `dsoxlab run`, `dsoxlab check`
doit rendre **0**, puisque le travail n'est pas fait. Après la solution de
référence, il doit rendre **100**. Un test qui passe avant le travail ne mesure
rien, et c'est le défaut le plus coûteux du domaine.

## Jouer un lab

```bash
export LAB_HOME=$PWD
dsoxlab use --provider kvm     # une liste de providers ne se résout pas seule
dsoxlab provision              # crée la machine, une fois
dsoxlab list-labs              # le catalogue
dsoxlab run   <id>             # pose l'état initial et ouvre la session
dsoxlab check <id>             # joue les tests et calcule le score
dsoxlab hint  <id>             # un indice, au prix de points
dsoxlab clean <id>             # défait le lab, garde la machine
dsoxlab destroy                # rend la machine
```

## La machine, et pourquoi une seule

Une machine virtuelle, déclarée dans `meta.yml` et provisionnée par
`dsoxlab provision` :

| Hôte | Distribution | vCPU | RAM | Disque |
|---|---|---|---|---|
| `idp.lab` | Ubuntu 24.04 | 2 | 6 Go | 30 Go |

Tout y tourne en conteneurs : Keycloak, sa base PostgreSQL, l'annuaire LLDAP,
l'application témoin et l'API témoin. Deux labs demandent davantage, et ce sont
eux qui fixent les 6 Go plutôt que les 4 du minimum :

- `iam-11-federation-externe` lance un **second Keycloak**, qui joue le
  fournisseur d'identité de l'entreprise partenaire. Un compte chez un
  fournisseur public rendrait le lab injouable hors ligne et dépendant d'un
  service que personne ne contrôle ;
- `iam-14-plateforme` monte un **cluster k3d dans la machine**, pour brancher
  son serveur d'API sur le fournisseur d'identité.

Rien ne tourne sur le poste de l'apprenant : un fournisseur d'identité qui
écoute sur la machine de travail finit par entrer en conflit avec autre chose,
et ce n'est pas ce que le lab enseigne.

## Le parcours

Deux niveaux, dans l'ordre du jeu. Il ne suit pas la numérotation des fiches :
les labs 11 et 12 se jouent au module 4, le 13 au module 6, le 14 au module 7.

### Niveau 1 : brancher une application sur un fournisseur d'identité

Installer Keycloak avec sa base, brancher une application en OIDC avec PKCE,
mettre une API derrière des jetons d'accès, fédérer un annuaire puis un service
SAML, déléguer à un fournisseur externe, et diagnostiquer une intégration qui
échoue. Se termine par l'épreuve de niveau.

### Niveau 2 : exploiter et gouverner

Imposer une authentification forte, traiter le départ d'un collaborateur,
conduire une revue des accès, brancher la plateforme, sauvegarder et mettre à
jour le fournisseur, et décrire le realm en tant que code. Se termine par
l'épreuve finale.

## Les solutions sont chiffrées

L'apprenant doit chercher. Les solutions de référence vivent donc sous
`solution/<lab>/`, chiffrées par `ansible-vault`, et le mot de passe
(`.vault-pass` à la racine) n'est jamais versionné. Un fichier de solution en
clair est un défaut, que `tests/test_solutions_chiffrees.py` refuse.

Le tutoriel d'un lab n'en donne jamais la réponse non plus : il enseigne chaque
mécanisme sur un exemple jetable, aux noms volontairement étrangers au
challenge, que l'apprenant doit ensuite transposer.

## Ce dépôt n'est pas la CLI

Un défaut du moteur se corrige dans [dsoxlab](https://github.com/stephrobert/dsoxlab),
ou se remonte en issue. Ici, tout ce qui pilote la CLI est déclaratif :
`meta.yml` pour le catalogue, `lab.yaml` par lab, `setup.yaml` et `cleanup.yaml`
pour la machine, `challenge/tests/test_functional.py` pour la preuve.

## Licence

[CC BY 4.0](./LICENSE).
