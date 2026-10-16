# Quelqu'un a changé quelque chose

Le realm fonctionne. Il a fallu trois semaines de clics dans la console pour y
arriver, étalées sur quatre mois, par cinq personnes, et il fonctionne.
Personne ne sait dire ce qu'il contient. Il existe une page de wiki qui liste
les clients, écrite en mars, et deux de ces clients n'existent plus.

Mardi dernier, quelque chose a cessé de marcher pour une application, et
l'enquête a trouvé qu'une durée de jeton était passée de dix à trente minutes.
Le changement est dans le journal des événements d'administration, avec une
date et un nom de compte. Le compte appartient à quelqu'un qui ne travaille
plus ici, et le journal dit ce qui a été changé, pas pourquoi.

C'est le vrai coût d'une configuration qui ne vit que dans le serveur : non pas
qu'elle dérive, mais que rien ne permet de distinguer un changement voulu d'une
erreur. Les deux apparaissent de la même façon, les deux sont déjà en
production, et le seul enregistrement de l'intention est la mémoire de
quelqu'un.

Vous allez donc l'écrire. Pas dans une page de wiki, qui dérive sans le dire à
personne, mais dans des fichiers qu'un outil lit et fait respecter, pour que la
question « que devrait contenir ce realm » ait une seule réponse, et que la
question « quelqu'un l'a-t-il changé » se règle par une commande plutôt que par
une enquête.

Vous décrirez un petit realm : deux rôles, un groupe, un client public et un
client confidentiel. Puis vous l'appliquerez, changerez quelque chose à la main
comme le changement de mardi a été fait, et regarderez les fichiers reprendre
le realm.

Deux avertissements, tous deux sur ce que « versionné » implique.

Un client confidentiel a un secret. Ne pas écrire ce secret dans vos fichiers
est le geste évident, et il ne suffit pas : l'outil garde une trace de tout ce
qu'il gère, et cette trace est un fichier sur le disque, avec les droits par
défaut. Allez le regarder avant de décider que vous avez fini.

Et l'outil s'authentifie quelque part pour faire son travail. Ce quelque part
est un realm, et ce n'est pas celui que vous décrivez. Confondez les deux et
vous appliquerez votre spécification sur le realm d'administration, ou sur
celui dont les autres labs dépendent, et la notation vérifie les deux.
