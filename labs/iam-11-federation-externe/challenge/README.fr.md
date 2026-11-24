# Quinze consultants, et aucun compte pour eux

## La situation

L'entreprise partenaire envoie quinze consultants pour six mois. Il leur faut
l'accès à trois de vos applications, et ils ont déjà des comptes : chez leur
propre employeur, qui gère leurs mots de passe, leurs seconds facteurs et,
surtout, leurs départs.

Vous pourriez créer quinze comptes. Tout le monde le fait, la première fois.
Puis quelqu'un quitte l'entreprise partenaire en mars, personne ne vous le dit,
et son compte fonctionne jusqu'au jour où quelqu'un pense à poser la question.

L'autre voie est de laisser leur employeur répondre pour eux. Votre realm
devient un **courtier** : quand un consultant se connecte, il l'envoie chez le
partenaire, le partenaire l'authentifie, et votre realm crée un compte local
rattaché à cette réponse. Le mot de passe ne vient jamais chez vous, et le jour
où le consultant quitte le partenaire, le refus du partenaire est votre refus.

Cette partie est simple, et ce n'est pas là que passe l'après-midi.

L'après-midi passe dans la question que personne ne pose à voix haute : **que
reçoit exactement un inconnu en arrivant ?** Un compte sans groupe n'a aucun
droit et ne sert à rien. Un compte rangé à la main a ce dont la personne qui
l'a rangé s'est souvenue. Et un compte qui arrive avec un rôle
d'administration est une porte que plus personne ne regardera.

Il y a encore une chose, et c'est le tranchant de tout ce lab. Votre realm
contient déjà un compte qui porte la même adresse qu'une des personnes du
partenaire. Les adresses se télescopent : les gens changent d'employeur, des
sociétés fusionnent, quelqu'un a mal saisi quelque chose en 2019. Si votre flux
de premier login traite une adresse qui correspond comme une preuve d'identité,
alors l'inconnu du partenaire est désormais cette personne. Aucune alerte,
aucune trace, rien à remarquer.

Deux personnes du partenaire se connecteront pendant la notation. L'une doit
entrer. L'autre, non.

## Ce qu'un inconnu reçoit en arrivant

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

### Ce qui est attendu

1. Un **fournisseur d'identité OIDC** d'alias `oidc-partenaire`, activé, pointé
   sur le partenaire, qui **vérifie** la signature de ses jetons contre les clés
   que le partenaire publie.
2. Un groupe nommé **`partenaires`**, déclaré comme **groupe par défaut du
   realm**. Créer le groupe ne suffit pas.
3. Le flux de premier login ne doit **pas** lier un inconnu à un compte local
   existant sur la foi d'une adresse qui correspond.

Puis deux connexions, et c'est là que la notation se joue.

### Ce qui est prouvé, et comment

Les tests jouent deux parcours, et en attendent des résultats **opposés** :

| Compte | Son adresse | Attendu |
|---|---|---|
| `dora` | ne correspond à personne | le parcours **aboutit**, le compte arrive dans `partenaires`, sans aucun rôle d'administration |
| `bob` | est celle de `chloe` | le parcours **s'arrête**, sur un écran qui nomme le conflit, et `chloe` est intacte |

Le second est celui qui compte. Un refus qu'on peut voir vaut mieux qu'un
réglage qu'on peut lire.

### Contraintes

- L'alias est **`oidc-partenaire`**. Le partenaire a déjà déclaré l'adresse de
  retour qu'il produit : en changer fait refuser toutes les connexions.
- Le client et son secret viennent **du partenaire**. N'en créez pas d'autres :
  l'échange de jeton serait refusé.
- Lisez les points d'accès du partenaire dans son **document de découverte**.
  Ses clés sont à **lire chez lui**, pas à recopier : un partenaire qui tourne
  ses clés ne doit pas casser votre courtier.

### Trois choses à savoir avant de commencer

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
