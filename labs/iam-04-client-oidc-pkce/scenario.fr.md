# L'application qui doit cesser de garder des mots de passe

L'application `notes` demande à ses utilisateurs un identifiant et un mot de
passe, les compare à sa propre table, et garde une session. Elle fonctionne.
Elle fonctionne depuis six ans.

Puis l'entreprise a acheté un deuxième outil, et un troisième. Chacun demande un
mot de passe. Chacun tient sa table. Quand quelqu'un part, il faut mettre trois
tables à jour, et le jour où l'on en oublie une, un ancien salarié lit encore
les notes.

Vous avez un fournisseur d'identité qui tourne : Keycloak, avec sa base, sur
`idp.lab`. La décision est prise, et elle ne se discute pas : `notes` cesse de
demander des mots de passe. Elle envoie l'utilisateur chez le fournisseur, et le
fournisseur le renvoie avec une preuve de qui il est.

Cette preuve est un jeton, et un jeton ne vaut que les contrôles qu'on fait sur
lui. L'application témoin sait déjà les faire, tous. Ce qu'elle ne sait pas,
c'est **à qui elle doit s'adresser**, et le fournisseur ignore encore que cette
application existe.

C'est tout le travail : déclarer l'application au fournisseur, déclarer le
fournisseur à l'application, et ne rien laisser d'ouvert qui doive être fermé.

Ce sur quoi vous serez noté n'est pas votre fichier de configuration. C'est ce
que le fournisseur **refuse** : un code échangé sans preuve d'origine, une
adresse de retour qui n'a jamais été déclarée, un octroi par mot de passe qui
laisserait l'application revoir le mot de passe. Une intégration qui fonctionne
et ne refuse rien est une intégration qui n'a pas été faite.
