# L'authentification, et personne pour la tenir

L'équipe vient de livrer trois applications internes en six mois. Chacune a son
propre écran de connexion, sa propre table d'utilisateurs, et sa propre façon
de perdre les mots de passe. Quand un collaborateur part, il faut penser à le
retirer de trois endroits, et personne ne sait dire s'il l'a été.

La décision est prise : un fournisseur d'identité, un seul, devant les trois.

Vous héritez de la machine qui doit l'héberger. Elle est nue, et c'est à vous
d'y faire tourner Keycloak comme un service qu'on laisse en production, pas
comme une démonstration qui s'évapore au premier redémarrage.

Deux choses comptent davantage que de voir l'écran de connexion apparaître.

La première est la **persistance**. Keycloak sait démarrer seul, sans base,
avec tout en mémoire ou dans un fichier qu'il garde pour lui. C'est commode
pour essayer, et c'est un piège en production : le jour où le conteneur
redémarre, les comptes, les applications déclarées et les sessions sont
partis. Vous adosserez donc Keycloak à une vraie base de données.

La seconde est le **compte d'administration**. Au premier démarrage, Keycloak
réclame un compte temporaire qu'on lui passe par une variable d'environnement,
visible de quiconque peut inspecter le conteneur. Ce compte sert à créer le
vrai, et ne doit pas lui survivre.
