# Challenge : une équipe, pas tout le monde

Le realm `formation` porte deux groupes et deux comptes, un dans chaque.
`/opt/iam-lab/identifiants-lab.txt` les nomme. Les deux ont le même mot de passe
et **aucun second facteur**.

L'application tourne sur le port `9080`.

## Ce qui est attendu

1. Une **copie** du flux de navigateur est le flux actif du realm. Celui que
   Keycloak fournit reste intact.
2. Dans cette copie, le second facteur est exigé **par rôle**, et le groupe
   `devops` porte ce rôle.
3. La condition `conditional-user-configured` a **disparu** du sous-flux du
   second facteur.
4. Une option **résistante au hameçonnage** est proposée à côté du code.
5. La politique de mot de passe du realm suit NIST SP 800-63B-4 : une longueur
   minimale sérieuse, **aucune règle de composition**, **aucune expiration**.

## Ce qui est prouvé, et comment

Sept tests. Celui qui décide de tout joue **deux connexions** :

| Compte | Son équipe | Attendu |
|---|---|---|
| `resp-exploitation` | `devops` | **arrêté**, sur un écran qui demande d'enregistrer un second facteur |
| `resp-lecture` | `lecteurs` | **passe** |

Les deux ont le même mot de passe et aucun second facteur. Seule leur
appartenance diffère, donc seule leur appartenance peut expliquer la différence.

Les autres tests vérifient que le flux fourni par Keycloak est intact, que le
flux actif est une copie, que la condition est un rôle et non
`user configured`, que le rôle est sur le **groupe** et non sur le compte,
qu'une option résistante au hameçonnage est proposée, et la politique de mot de
passe.

## Trois choses mesurées, et chacune coûte une après-midi

**Keycloak 26.8.1 n'a aucune condition de groupe.** Les conditions disponibles
sont le rôle, un attribut d'utilisateur, un identifiant, « user configured », un
scope de client, un niveau d'authentification et un sous-flux déjà joué. Cibler
une équipe passe par un **rôle**, que le groupe porte.

**`conditional-user-configured` est le piège.** Avec elle en place, le second
facteur n'est exigé que des gens qui en ont déjà un. Mesuré : un compte sans
second facteur se connecte directement, même avec l'étape OTP en `REQUIRED`.
Rien ne le signale.

**Une copie du flux de navigateur contient deux sous-flux conditionnels**,
chacun avec sa propre `conditional-user-configured`. Celle qui vit sous
*Conditional Organization* n'a rien à voir avec le second facteur et doit
rester. Retirez la mauvaise et le piège est toujours là.

## Sur la politique de mot de passe

NIST SP 800-63B-4 demande de la longueur et interdit le reste, et la raison est
mesurée plutôt que théorique. Les règles de composition produisent des mots de
passe devinables, parce que tout le monde satisfait la contrainte de la même
façon. L'expiration périodique produit des variantes incrémentées du même mot de
passe. Un rôle attaché au compte plutôt qu'au groupe, c'est un geste oublié par
arrivée.

```bash
dsoxlab check iam-07-mfa-keycloak   # noter
dsoxlab hint  iam-07-mfa-keycloak   # un indice, au prix de quelques points
```
