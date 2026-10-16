# Tout, sur une machine, avant la fin de la journée

L'audit est dans trois semaines. L'auditeur a envoyé sa liste de questions en
avance, ce qui est une politesse, et la liste est assez courte pour se lire en
une minute et assez longue pour expliquer pourquoi personne ne dort bien depuis.

Qui peut se connecter. Où vivent leurs comptes. Ce qui se passe quand quelqu'un
part. Si quelqu'un a un second facteur. Si vous pouvez prouver quoi que ce soit
de tout cela.

Pour l'instant les réponses honnêtes sont : personne ne sait, à quatre endroits,
rien, non, et non.

Vous avez une machine, un annuaire avec trois personnes dedans, une application
qui n'a pas de page de connexion, et une API qui répond à qui demande. Vous avez
jusqu'à la fin de la journée.

Ce que l'auditeur vérifiera n'est pas votre configuration. C'est si l'état du
système correspond à ce que vous lui avez dit. C'est donc ce que cette épreuve
vérifie aussi : seize lectures du système, dont aucune ne se soucie de la façon
dont vous y êtes arrivé.

Quatre de ces lectures méritent d'y penser avant de commencer.

**Le fournisseur doit survivre à un redémarrage.** Non parce que les
redémarrages sont fréquents, mais parce qu'un fournisseur qui perd son realm au
redémarrage n'a pas de realm : il a une démonstration.

**Le second facteur va au groupe sensible, et à lui seul.** Imposé à tout le
monde, il enferme l'administrateur dehors, et le remède habituel à ce moment-là
est de tout désactiver le lundi matin. Imposé à personne, ce qui arrive plus
souvent, il passe toutes les inspections visuelles : l'étape est là, elle est
obligatoire, et les gens qui n'ont aucun second facteur entrent directement.

**Le départ doit être terminé.** Trois gestes, et deux d'entre eux répondent
« fait » sans avoir rien fait. L'un d'eux est refusé par le fournisseur
lui-même, poliment, d'une façon qu'il faut aller chercher.

**La sauvegarde doit se restaurer.** Pas exister : se restaurer. Cette épreuve
crée une base, y met votre sauvegarde, et compte ce qui est revenu. Un export
du realm ne passera pas, et il ne passera pas pour une raison qui intéresse
l'auditeur : il ne contient aucune trace de qui s'est connecté.

Le cahier des charges est dans `/opt/iam-lab/identifiants-lab.txt`. Il nomme les
trois comptes et le rôle que chacun joue dans cette épreuve, et cette partie
mérite d'être lue attentivement : l'un des trois ne doit pas être dans le groupe
sensible, et le cahier des charges vous dit lequel.

Il n'y a aucun indice.
