# Personne ne se souvient pourquoi il l'a

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
