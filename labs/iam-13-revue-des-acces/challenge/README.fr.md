# Challenge : provisionner, automatiser, et trouver ce que la revue manque

Le realm `formation` porte trois comptes et deux groupes.
`/opt/iam-lab/identifiants-lab.txt` les nomme, nomme le rôle accordé
directement, dit qui le porte, et donne l'URL SCIM et où écrire la revue.

L'API SCIM est **fermée**, et il n'y a **aucun workflow**. Le setup vérifie les
deux avant de rendre la main.

## Ce qui est attendu

1. L'**API SCIM est ouverte** sur le realm, et répond `401` sans jeton plutôt
   que `404`.
2. Un client nommé **`scim-client`** existe : confidentiel, avec un compte de
   service, sans flux de code d'autorisation, et ne détenant que ce qu'il lui
   faut sur les comptes. Pas `realm-admin`.
3. Le jeton de ce client est **accepté** par l'API SCIM.
4. Le compte nommé dans `COMPTE_A_PROVISIONNER` a été créé **par l'API**, et se
   relit par elle.
5. Un **workflow** existe, qui **désactive** un compte. Pas un qui supprime.
6. Le fichier de revue liste tous les comptes avec leurs groupes **et leurs
   rôles**, et le rôle injustifié a été **retiré**, du realm et de la revue.

## Trois choses mesurées, chacune une après-midi

**La fonctionnalité est activée sur le serveur et l'API répond quand même 404.**
Elle s'ouvre par realm, et le drapeau vit à la **racine** de la représentation
du realm. Mettez-le dans les `attributes` du realm et la mise à jour rend `204`
pendant que la valeur se relit à faux. Rien ne le signale.

**Une fois ouverte, elle répond 401 avec des messages en forme SCIM.** Le jeton
de l'administrateur du realm `master` obtient « Bearer token required ». Un
jeton de client de ce realm obtient « Invalid token audience ».

**L'audience qu'elle veut est sa propre URL.** Trois candidats plausibles ont
été essayés avant celui-là. Donner une audience à un jeton, c'est le mappeur du
lab 05, réemployé.

## Sur le workflow

L'API prend un nom et des étapes, et elle **rend du YAML**, pas du JSON, ce qui
vaut d'être su avant d'essayer d'analyser sa réponse. Un `POST {}` vous dit ce
qu'elle attend.

Le verbe compte plus que la syntaxe. Il existe une étape qui supprime, et la
notation la refuse : une règle de cycle de vie qui détruit des comptes détruit
aussi les preuves, et elle le fait sans personne.

## Sur la revue

Même forme que celle du lab 8 : du JSON, une entrée par compte, chacune avec un
`username`, une clef de groupes et une clef `roles`. Elle doit être complète, et
décrire l'état **après** votre travail.

Ce qui est noté au-delà, c'est si vous avez **trouvé** la chose. La revue n'est
pas là pour être signée, elle est là pour trouver un accès que personne ne peut
justifier, et pour le retirer.

```bash
dsoxlab check iam-13-revue-des-acces   # noter
dsoxlab hint  iam-13-revue-des-acces   # un indice, au prix de quelques points
```
