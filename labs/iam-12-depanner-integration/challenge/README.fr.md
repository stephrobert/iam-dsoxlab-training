# Challenge : trouver la cause, et ne corriger que celle-là

Le fournisseur tourne sur `idp.lab`, realm `formation`. L'application tourne
sur le port `9080`, et sa connexion échoue.
`/opt/iam-lab/identifiants-lab.txt` porte le compte de test et l'emplacement du
fichier de configuration de l'application.

**Le setup a tiré une panne au hasard parmi cinq.** Vous ne savez pas laquelle,
et rien sur la machine ne vous le dira. Quatre vivent dans le fournisseur, une
vit dans l'application.

Le **journal d'événements du realm est activé**, ce qui n'est pas le défaut.
Servez-vous en.

## Ce qui est attendu

La connexion remarche, et l'état final est le bon :

1. le client `appli-notes` existe, **activé**, **public**, sans secret ;
2. seul le **flux de code d'autorisation** est ouvert ;
3. **PKCE en S256** est exigé, et le serveur refuse un échange sans lui ;
4. l'URI de redirection est **exactement** celle de l'application, sans joker ;
5. l'`issuer` de l'application pointe le realm `formation`.

## Ce qui est prouvé, et comment

Six tests. Le premier joue tout le parcours et vérifie que l'application finit
par afficher l'utilisateur connecté, avec un ID token validé.

Les cinq autres vérifient que vous n'avez **pas** pris l'un de ces raccourcis :

| Raccourci | Ce qu'il cache | Ce qu'il ouvre |
|---|---|---|
| une URI de redirection en joker | `invalid_redirect_uri` | un attaquant reçoit le code d'autorisation |
| un client confidentiel, son secret dans l'appli | `unauthorized_client` | le secret est lisible par qui installe l'appli |
| PKCE désactivé | toute une classe d'erreurs | un code intercepté suffit à obtenir un jeton |
| l'octroi par mot de passe ouvert | un flux de code fermé | l'application voit le mot de passe |
| l'`issuer` déplacé ailleurs | un client introuvable | une connexion qui réussit, avec les mauvaises gens |

Le dernier mérite attention : pointer l'application sur un autre realm produit
une connexion qui **marche**. Elle authentifie simplement la mauvaise
population.

## Où regarder, dans l'ordre

```bash
# 1. Que dit le fournisseur ? Jouez le parcours et lisez le message.
python3 /opt/iam-lab/outils/parcours.py \
  --depart http://127.0.0.1:9080/connexion \
  --utilisateur alice --mot-de-passe "$(grep '^MOT_DE_PASSE=' \
    /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)" \
  --attendre-texte "Connecté" | jq -r '.texte, .arrivee'
```

Puis le journal d'événements, qui nomme la cause en un mot. Puis l'état de
l'application elle-même, sur `http://127.0.0.1:9080/etat`, qui dit ce qu'elle a
lu et ce qu'elle a refusé.

## Une chose à laquelle résister

Quand vous trouvez la cause, corrigez **celle-là**. La tentation est de la
corriger et, puisqu'on est dans l'écran, de relâcher deux autres choses qui ont
l'air suspectes. Chacune est un test que vous perdrez, et en production chacune
est un incident qui attend.

```bash
dsoxlab check iam-12-depanner-integration   # noter
dsoxlab hint  iam-12-depanner-integration   # un indice, au prix de quelques points
```
