# Challenge : une API qui pose les bonnes questions

Le fournisseur tourne sur `idp.lab`, port `8080`, realm `formation`. L'API
tourne sur le port `8090`, depuis `/opt/iam-lab/api-notes/api.py`, et elle est
déjà démarrée.

`/opt/iam-lab/identifiants-lab.txt` porte le compte de test et les noms des
objets que le setup a posés pour vous.

## Ce qui est déjà là, et à quoi cela sert

| Nom | Ce que c'est |
|---|---|
| `notes-cli` | un client public avec l'octroi direct, pour obtenir des jetons en ligne de commande |
| `autre-api` | une seconde API, déclarée pour une seule raison : être une audience qui n'est pas la vôtre |
| `autre:lecture` | son scope, qui porte son audience. Demandez-le et vous obtenez un jeton valide destiné à quelqu'un d'autre |
| `alice` | le compte humain du lab |

Commencez par vous en servir. Obtenez un jeton avec `autre:lecture`, appelez
`GET /notes` avec lui, et regardez l'API répondre `200`. C'est l'état que vous
venez corriger.

## Ce qui est attendu

1. L'API est déclarée comme **client** nommé **`notes-api`**, sans aucun flux.
   Son identifiant de client est ce que les jetons nommeront comme audience.
2. Deux **scopes** existent, `notes:lecture` et `notes:ecriture`, un par
   permission. Chacun porte l'**audience** de `notes-api`.
3. L'API vérifie **quatre** revendications, pas une : signature, émetteur,
   audience et expiration. Puis elle vérifie le **scope** que la route exige.
4. Un **service de sauvegarde** a un accès machine : un client confidentiel
   nommé **`service-sauvegarde`**, avec un compte de service, qui détient la
   **lecture seule**.
5. Le secret du service n'est écrit dans **aucun fichier**.

## Ce qui est prouvé, et comment

Les tests ne lisent pas votre code. Ils envoient des jetons et lisent ce que
l'API répond :

- sans jeton, `401` avec un en-tête `WWW-Authenticate` ;
- un jeton de la bonne audience et du bon scope, `200` ;
- un jeton destiné à `autre-api`, `401` ;
- un jeton de lecture seule sur une écriture, `403` nommant
  `insufficient_scope` ;
- le jeton du service, `200` en lecture et `403` en écriture.

La distinction entre `401` et `403` est notée, et elle n'est pas cosmétique.
`401` dit « je ne sais pas qui vous êtes », et un client réessaie en
s'authentifiant. `403` dit « je sais qui vous êtes, et cela ne suffit pas », et
réessayer ne sert à rien.

## Contraintes

- Les noms sont imposés : `notes-api`, `service-sauvegarde`, `notes:lecture`,
  `notes:ecriture`. Les tests les cherchent.
- `GET` exige la lecture, `POST` exige l'écriture.
- Lancez l'API avec l'interpréteur
  `/opt/iam-lab/appli-temoin/.venv/bin/python`, qui porte les dépendances
  épinglées. Le `python3` du système n'a aucune bibliothèque JWT.
- Ne touchez ni à `autre-api` ni à `notes-cli` : ce sont les instruments de
  mesure.

## Deux pièges qui ont coûté une après-midi à d'autres

**Un scope ne change pas l'audience.** Déclarer `notes:lecture` ne met rien
dans `aud`. L'audience arrive par un mappeur de protocole posé sur le scope,
qui nomme le client visé. Sans lui, les jetons restent adressés à `account`, et
l'API ne peut pas savoir qu'ils sont pour elle. C'est le seul point qui arrête
la plupart des gens.

**Un service n'a personne pour demander un scope.** En client credentials,
seuls les scopes **par défaut** du client arrivent dans le jeton. Attachez le
scope de lecture en optionnel et le service obtient un jeton sans aucune
permission, pendant que tous les tests sur les utilisateurs continuent de
passer.

```bash
dsoxlab check iam-05-api-protegee   # noter
dsoxlab hint  iam-05-api-protegee   # un indice, au prix de quelques points
```
