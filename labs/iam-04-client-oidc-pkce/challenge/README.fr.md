# L'application qui doit cesser de garder des mots de passe

## La situation

L'application `notes` demande à ses utilisateurs un identifiant et un mot de
passe, les compare à sa propre table, et garde une session. Elle fonctionne.
Elle fonctionne depuis six ans.

Puis l'entreprise a acheté un deuxième outil, et un troisième. Chacun demande un
mot de passe. Chacun tient sa table. Quand quelqu'un part, il faut mettre trois
tables à jour, et le jour où l'on en oublie une, un ancien salarié lit encore
les notes.

Vous avez un fournisseur d'identité qui tourne : Keycloak, avec sa base, sur
`idp.lab`. La décision est prise, et elle ne se discute pas : `notes` cesse de
demander des mots de passe. Elle envoie l'utilisateur chez le fournisseur, et le
fournisseur le renvoie avec une preuve de qui il est.

Cette preuve est un jeton, et un jeton ne vaut que les contrôles qu'on fait sur
lui. L'application témoin sait déjà les faire, tous. Ce qu'elle ne sait pas,
c'est **à qui elle doit s'adresser**, et le fournisseur ignore encore que cette
application existe.

C'est tout le travail : déclarer l'application au fournisseur, déclarer le
fournisseur à l'application, et ne rien laisser d'ouvert qui doive être fermé.

Ce sur quoi vous serez noté n'est pas votre fichier de configuration. C'est ce
que le fournisseur **refuse** : un code échangé sans preuve d'origine, une
adresse de retour qui n'a jamais été déclarée, un octroi par mot de passe qui
laisserait l'application revoir le mot de passe. Une intégration qui fonctionne
et ne refuse rien est une intégration qui n'a pas été faite.

## Une intégration qui refuse ce qu'elle doit refuser

Le fournisseur tourne sur `idp.lab`, sur le port `8080`, avec un realm nommé
`formation` et un compte dedans. `/opt/iam-lab/identifiants-lab.txt` porte ce
compte.

L'application témoin vit dans `/opt/iam-lab/appli-temoin`. Elle est complète :
elle sait déjà démarrer un flux de code d'autorisation avec PKCE, et valider
l'ID token qu'elle reçoit jusqu'à son nonce. Lire son code ne vous donnera pas
la réponse, parce que la réponse vit dans le fournisseur.

### Ce qui est attendu

1. L'application a une identité auprès du fournisseur : un client nommé
   **`appli-notes`**, dans le realm `formation`.
2. Ce client est **public** et ne porte aucun secret.
3. Seul le **flux de code d'autorisation** est ouvert. Les trois autres octrois
   sont fermés, et l'un d'eux est ouvert par défaut.
4. **PKCE en S256** est exigé, pas seulement proposé.
5. Les **URI de redirection sont exactes**. Aucun joker, nulle part.
6. L'application connaît le fournisseur : `configuration.json`, à côté de
   `appli.py`, déclare l'`issuer`, le `client_id` et la `redirect_uri`.
7. L'application **tourne**, et un utilisateur du realm peut s'y connecter.

### Ce qui est prouvé, et comment

Les tests n'ouvrent pas votre configuration. Ils interrogent l'API
d'administration du fournisseur, puis ils **jouent le flux**, comme un
navigateur le ferait :

- un code échangé **sans** `code_verifier` doit être refusé ;
- une URI de redirection jamais déclarée doit être refusée ;
- l'ID token doit porter l'émetteur de ce realm, l'audience de ce client, et le
  nonce qui a été envoyé ;
- la page de l'application doit finir par afficher le nom de l'utilisateur
  connecté.

Un attribut posé sans effet est le piège que cette notation existe pour
attraper. Il ne suffit pas que la fiche du client annonce PKCE : il faut que le
serveur refuse sans lui.

### Contraintes

- Le client s'appelle `appli-notes`. Les tests le cherchent sous ce nom.
- L'application écoute sur le port **9080**, et son chemin de retour est
  **`/callback`**. L'hôte et le port de l'URI de redirection vous
  appartiennent ; le chemin, non.
- Lancez l'application avec l'interpréteur de son propre environnement
  virtuel, `.venv/bin/python`, et non le `python3` du système : il lui faut ses
  dépendances épinglées pour valider une signature.
- Ne modifiez pas le compte de `identifiants-lab.txt` : les tests s'y
  connectent.

### Deux pièges qui ont coûté une après-midi à d'autres

Un client créé sans y penser arrive avec l'**octroi par mot de passe activé**.
C'est le seul octroi qui ruine tout le propos : l'application revoit le mot de
passe, ce que la délégation de connexion devait précisément empêcher. Rien ne
vous avertit, et le flux fonctionne parfaitement avec lui ouvert.

Un realm sert une population. Le realm des administrateurs du serveur n'est pas
celui des utilisateurs d'une application. Un `issuer` qui pointe le mauvais
realm donne un flux qui réussit, avec les mauvaises personnes.

```bash
dsoxlab check iam-04-client-oidc-pkce   # noter
dsoxlab hint  iam-04-client-oidc-pkce   # un indice, au prix de quelques points
```
