# Lundi matin, et rien n'est branché

L'entreprise a un annuaire. Il est là depuis des années, il porte les trois
personnes qui utiliseront ce que vous allez construire aujourd'hui, et il
fonctionne. C'est la seule chose qui fonctionne.

Il n'y a pas de fournisseur d'identité. Il y a une application qui affiche des
notes, et une API qui les sert, et les deux ont été écrites par quelqu'un qui
est parti. L'application n'a pas de page de connexion. L'API répond à qui
demande, et c'est ainsi que les notes se sont retrouvées dans un ticket de
support le mois dernier, collées par quelqu'un qui n'était pas censé les voir.

Vous avez la machine, l'annuaire, et jusqu'à la fin de la matinée.

Ce qui est attendu n'est pas une démonstration. C'est un fournisseur qui est
encore là après le redémarrage de la machine, un annuaire dont les comptes et
les groupes sont utilisables à travers lui, une application qui envoie les gens
chez le fournisseur et affiche leur nom quand ils reviennent, et une API qui
refuse ce qu'elle doit refuser.

Cette dernière est la partie que l'on rate, et on la rate d'une façon précise :
on fait vérifier à l'API que le jeton est valide. Un jeton de ce fournisseur,
pour cette personne, émis pour une application entièrement différente, est
valide. Si cela suffit à votre API, alors toutes les applications du realm
peuvent lire les notes, et vous avez reconstruit le ticket du mois dernier avec
plus d'étapes.

Il n'y a aucun indice dans cet exercice. Les tests lisent l'état du système,
donc la façon d'y arriver vous appartient : console, API, script, cela ne change
rien. Ce qui compte est ce qui est vrai à la fin.

Le cahier des charges est dans `/opt/iam-lab/identifiants-lab.txt`. Il nomme
tout ce que les tests cherchent, parce qu'une épreuve qui cacherait les noms
mesurerait de la devinette.
