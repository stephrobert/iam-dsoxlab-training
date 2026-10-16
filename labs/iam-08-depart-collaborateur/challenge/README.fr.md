# Challenge : quatre gestes, dans le bon ordre

L'annuaire est fédéré dans le realm `formation`, en lecture seule, avec son
mappeur de groupes. Quatre personnes y figurent, et `morgane` part.

`/opt/iam-lab/identifiants-lab.txt` nomme qui part, qui reste, le rôle accordé
directement, et où écrire la revue.
`/opt/iam-lab/jetons-de-la-session.txt` porte les jetons d'une session que le
setup a ouverte pour elle : les tests s'en servent, ne les modifiez pas.

## Ce qui est attendu

1. `morgane` n'appartient plus à aucun groupe, et ne détient plus le rôle qui
   lui avait été accordé directement.
2. Son compte est **désactivé**, et **toujours présent**.
3. Elle n'a **aucune session active**.
4. Son jeton de rafraîchissement est refusé.
5. Un fichier de revue existe au chemin donné, listant **tous** les comptes
   avec leurs groupes **et** leurs rôles accordés directement, et reflétant
   l'état **après** le départ.

Et les trois personnes qui restent doivent être intactes.

## Trois choses qui échouent en silence

**Une session survit à la désactivation.** Mesuré : après avoir passé le compte
à désactivé, il compte encore une session active. La fiche du compte dit
« désactivé ». La session continue. Il faut la fermer.

**Le fournisseur refuse de retirer une appartenance fédérée**, et il a raison :
`Not possible to delete LDAP group mappings as mapper mode is READ_ONLY`.
L'annuaire possède cette appartenance. Retirez-la à la source.

**Le fournisseur garde en cache sa vue d'un compte fédéré.** Après le retrait à
la source ET la synchronisation du mappeur, il rend toujours les anciens
groupes, et la synchronisation répond pourtant `5 updated groups`. Il y a une
troisième chose à faire.

## Et une chose que l'ordre décide

Une synchronisation **ne reprend pas un compte désactivé**. Désactivez d'abord,
et l'appartenance que vous avez retirée à la source reste dans le fournisseur
pour de bon, sans erreur nulle part. Les gestes ont un ordre, et ce n'est pas
celui que l'urgence suggère.

## Le fichier de revue

Du JSON, au chemin donné par `identifiants-lab.txt`. Une entrée par compte,
chacune nommant le compte, ses groupes et ses rôles. La forme vous appartient
pourvu que chaque entrée porte un `username`, une clef `groupes` ou `groups`, et
une clef `roles`.

Deux choses y sont notées : elle doit être **complète**, et décrire l'état
**après** votre travail. Une revue écrite avant les retraits décrit un monde qui
n'existe plus, ce qui est pire que pas de revue du tout.

Les rôles comptent autant que les groupes. `morgane` en détient un accordé
directement à son compte, et une revue par groupes seuls ne le montrerait
jamais. C'est pour cela qu'il est dans ce lab.

```bash
dsoxlab check iam-08-depart-collaborateur   # noter
dsoxlab hint  iam-08-depart-collaborateur   # un indice, au prix de quelques points
```
