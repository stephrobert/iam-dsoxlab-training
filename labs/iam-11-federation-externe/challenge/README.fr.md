# Challenge : ce qu'un inconnu reçoit en arrivant

Deux realms sur `idp.lab`, servis par le même Keycloak.

| Realm | Rôle | État |
|---|---|---|
| `formation` | **courtier**, le vôtre | porte un compte local `chloe`, et le client de l'application témoin |
| `entreprise-externe` | le partenaire | porte `dora` et `bob`, et un client qu'il a déclaré pour vous |

`/opt/iam-lab/identifiants-lab.txt` porte l'URL de découverte du partenaire, le
client et le secret **que le partenaire vous a donnés**, l'alias attendu, les
deux comptes et leur mot de passe.

L'application témoin tourne sur le port `9080`, pointée sur votre courtier, et
elle demande directement le fournisseur d'identité nommé `oidc-partenaire`.

## Ce qui est attendu

1. Un **fournisseur d'identité OIDC** d'alias `oidc-partenaire`, activé, pointé
   sur le partenaire, qui **vérifie** la signature de ses jetons contre les clés
   que le partenaire publie.
2. Un groupe nommé **`partenaires`**, déclaré comme **groupe par défaut du
   realm**. Créer le groupe ne suffit pas.
3. Le flux de premier login ne doit **pas** lier un inconnu à un compte local
   existant sur la foi d'une adresse qui correspond.

Puis deux connexions, et c'est là que la notation se joue.

## Ce qui est prouvé, et comment

Les tests jouent deux parcours, et en attendent des résultats **opposés** :

| Compte | Son adresse | Attendu |
|---|---|---|
| `dora` | ne correspond à personne | le parcours **aboutit**, le compte arrive dans `partenaires`, sans aucun rôle d'administration |
| `bob` | est celle de `chloe` | le parcours **s'arrête**, sur un écran qui nomme le conflit, et `chloe` est intacte |

Le second est celui qui compte. Un refus qu'on peut voir vaut mieux qu'un
réglage qu'on peut lire.

## Contraintes

- L'alias est **`oidc-partenaire`**. Le partenaire a déjà déclaré l'adresse de
  retour qu'il produit : en changer fait refuser toutes les connexions.
- Le client et son secret viennent **du partenaire**. N'en créez pas d'autres :
  l'échange de jeton serait refusé.
- Lisez les points d'accès du partenaire dans son **document de découverte**.
  Ses clés sont à **lire chez lui**, pas à recopier : un partenaire qui tourne
  ses clés ne doit pas casser votre courtier.

## Trois choses à savoir avant de commencer

**Un groupe par défaut est une propriété du realm, pas du groupe.** Créer
`partenaires` n'y met personne. C'est le realm qui doit le désigner comme
groupe par défaut.

**Un groupe par défaut s'applique à la création du compte.** Déclarez-le après
la première connexion et le compte déjà créé reste dehors, ce qui ressemble
exactement à un groupe par défaut qui ne fonctionne pas. Supprimez le compte
rattaché et reconnectez-vous.

**Le flux de premier login de Keycloak vous protège déjà.** Il crée le compte
quand l'identité est nouvelle, et quand une adresse existe déjà, il demande une
confirmation et une vérification. Le travail consiste ici à **ne pas** le
remplacer par quelque chose qui lie à l'aveugle. Si vous cherchez un réglage à
activer, vous cherchez la mauvaise chose.

```bash
dsoxlab check iam-11-federation-externe   # noter
dsoxlab hint  iam-11-federation-externe   # un indice, au prix de quelques points
```
