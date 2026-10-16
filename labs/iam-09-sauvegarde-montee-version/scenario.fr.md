# La sauvegarde que personne n'a jamais restaurée

La montée de version est prévue jeudi soir. Le fournisseur a deux versions
mineures de retard, l'une porte un correctif dont quelqu'un a besoin, et la
demande de changement dit, sous la rubrique « plan de retour arrière », les mots
« restaurer depuis la sauvegarde ».

Il existe une sauvegarde. Elle tourne chaque nuit, elle n'a jamais échoué, et
personne ne l'a jamais restaurée. Ces deux faits sont d'ordinaire énoncés comme
une seule phrase rassurante, et ce ne sont pas du tout le même fait. Une
sauvegarde qu'on n'a jamais restaurée est un fichier dont personne n'a vérifié
le contenu, produit par une commande dont personne ne lit le code de retour, au
sujet d'une base dont la forme a changé deux fois depuis que le script a été
écrit.

Il existe aussi un export. Quelqu'un a exporté le realm le mois dernier, avant
un changement de configuration, et a gardé le fichier. Il dort dans un
répertoire partagé nommé `sauvegardes`, et c'est quatre cents kilo-octets de
JSON qui a l'air complet, avec le realm, les clients, les flux
d'authentification et les clefs, tout y est.

Ce n'est pas une sauvegarde, et la façon dont ce n'en est pas une vaut votre
après-midi. Le fichier que quelqu'un a gardé est l'un des deux que la commande
d'export produit, et c'est celui qui ne contient aucun compte. Restaurez depuis
lui vendredi matin et vous aurez un realm avec tous ses réglages en place, tous
ses clients configurés, et personne qui puisse se connecter.

Ce qu'il ne contient pas non plus, quel que soit le fichier que vous gardez,
c'est la trace de qui s'est connecté et quand. Cette trace vit dans la base,
dans des tables que l'export ne regarde pas. Perdez-la dans une montée de
version et la question « qui avait accès en mars » cesse d'avoir une réponse,
définitivement.

Donc : une instance tourne, avec une version de retard, des comptes, des
clients et quelques jours de trace d'audit. Sauvegardez-la correctement,
montez-la de version, puis prouvez que rien n'est perdu, ce qui veut dire le
prouver pour la trace autant que pour les comptes.

L'ordre compte, et c'est la seule partie de ce lab qu'on ne peut pas rattraper
après.
