# L'API qui fait confiance à toutes les signatures

L'API `notes` est protégée. Quelqu'un l'a dit à la dernière revue, et c'est vrai
en un sens : elle refuse un appel sans jeton, et elle refuse un jeton dont la
signature ne tient pas. Cela a été testé. Cela fonctionne.

La semaine dernière, l'entreprise a ajouté une seconde API, pour les factures.
Même fournisseur, même realm, mêmes clés. Un développeur qui branchait le client
des factures a remarqué une chose en débogant : le jeton délivré à son client,
destiné à l'API des factures, ouvrait aussi `notes`. Toutes les notes, de tous
les utilisateurs, avec un jeton qui n'avait jamais été prévu pour ce service.

Rien n'était cassé. Aucune clé n'a fui, aucun défaut dans la vérification de la
signature. L'API n'a simplement jamais posé la seule question qui comptait :
**ce jeton est-il pour moi ?**

Une signature prouve d'où vient un jeton. Elle ne dit rien de qui il est
destiné, ni s'il est encore valide, ni ce que son porteur a le droit de faire.
Ce sont trois revendications distinctes, et une API qui les ignore est ouverte à
quiconque détient n'importe quel jeton du même fournisseur.

Vous avez l'API, dans cet état exact, en service sur `idp.lab`. Vous avez aussi
une seconde API déclarée à côté, pour une seule raison : vous délivrer un jeton
parfaitement valide et simplement pas le vôtre. Servez-vous en. Regardez l'API
l'accepter.

Puis fermez cela, et pendant que vous y êtes, le service de sauvegarde a besoin
d'un accès lui aussi. Il n'a pas d'utilisateur, il tourne à trois heures du
matin, et il ne fait jamais que lire. Donnez-lui exactement cela, et rien de
plus : un compte machine que personne ne surveille et qui peut écrire est la
façon dont les données disparaissent sans bruit.
