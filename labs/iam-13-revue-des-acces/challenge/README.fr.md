# Personne ne se souvient pourquoi il l'a

## La situation

La revue trimestrielle des accès arrive sous forme de tableur. Quelqu'un exporte
la liste des comptes, quelqu'un d'autre coche les cases, et une troisième
personne signe. Cela prend une après-midi et cela ne trouve rien, chaque
trimestre.

Cela ne trouve rien à cause de la façon dont c'est bâti. L'export liste les
comptes et leurs groupes, parce que c'est ce que la console montre sur un seul
écran. Les groupes sont la partie propre : ils ont des noms, des responsables,
une raison d'exister.

La partie sale est ailleurs. Quelqu'un a eu besoin d'un accès à la production un
mardi de mars, pendant un incident. Il lui a été accordé directement sur son
compte, et non par un groupe, parce qu'un groupe aurait demandé un ticket et
deux validations et que l'incident, c'était maintenant. Cela a marché. Cela n'a
jamais été retiré. Cela n'apparaît dans aucune liste de groupes, et la revue qui
liste les groupes l'a validé trois fois.

Vous avez cette situation exacte : trois comptes, deux groupes, et un rôle
accordé directement à quelqu'un, avec une description qui dit ce qui s'est passé
et admet qu'il n'y avait pas de ticket.

Deux autres choses sont à faire pendant que vous y êtes, et les deux consistent
à en faire moins à la main.

L'arrivée d'un nouveau collègue ne devrait pas être un formulaire que quelqu'un
remplit. Le fournisseur a une API de provisionnement, fermée par défaut, qu'un
outil peut appeler. Ouvrez-la, donnez-lui un client qui sait faire exactement
cela et rien d'autre, et créez quelqu'un avec elle.

Et le départ de quelqu'un qui cesse simplement de venir ne devrait pas attendre
une revue non plus. Le fournisseur sait jouer un workflow sur une échéance.
Écrivez celui qui désactive un compte inactif, et prenez garde au verbe : il
existe une option qui supprime, et elle détruirait les preuves en même temps que
l'accès, toute seule, à trois heures du matin.

## Provisionner, automatiser, et trouver ce que la revue manque

Le realm `formation` porte trois comptes et deux groupes.
`/opt/iam-lab/identifiants-lab.txt` les nomme, nomme le rôle accordé
directement, dit qui le porte, et donne l'URL SCIM et où écrire la revue.

L'API SCIM est **fermée**, et il n'y a **aucun workflow**. Le setup vérifie les
deux avant de rendre la main.

### Ce qui est attendu

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

### Trois choses mesurées, chacune une après-midi

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

### Sur le workflow

L'API prend un nom et des étapes, et elle **rend du YAML**, pas du JSON, ce qui
vaut d'être su avant d'essayer d'analyser sa réponse. Un `POST {}` vous dit ce
qu'elle attend.

Le verbe compte plus que la syntaxe. Il existe une étape qui supprime, et la
notation la refuse : une règle de cycle de vie qui détruit des comptes détruit
aussi les preuves, et elle le fait sans personne.

### Sur la revue

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
