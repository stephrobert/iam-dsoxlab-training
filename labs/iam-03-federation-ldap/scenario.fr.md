# Deux listes de personnes, et personne ne sait laquelle est la bonne

L'annuaire porte les comptes de l'entreprise. Le fournisseur d'identité porte
les siens. Les deux ont été remplis à la main, à quelques semaines d'écart, et
ils dérivent depuis.

Quelqu'un est parti en juillet. Il a disparu de l'annuaire. Il se connecte
toujours par le fournisseur.

Le nom de famille de quelqu'un d'autre a été corrigé dans l'annuaire. Le
fournisseur affiche encore l'ancien sur tous les écrans, et personne ne peut
dire lequel est le vrai, parce que les deux font autorité et que les deux se
trompent.

Il n'y a qu'une sortie, et ce n'est pas un script de synchronisation. Le
fournisseur doit cesser de garder une copie, et commencer à **lire** l'annuaire.
Une source, une vérité, et une suppression qui prend effet partout parce qu'il
n'y a plus qu'un endroit où supprimer.

Keycloak sait le faire. Il fédère un annuaire : il lit les comptes, les importe
pour pouvoir y rattacher des groupes et des sessions, et refuse d'y réécrire.
Cette dernière partie compte plus qu'il n'y paraît. Un fournisseur autorisé à
écrire dans l'annuaire, c'est une correction faite dans une console qui change
la source, et au bout d'un mois personne ne sait plus d'où vient quoi.

L'annuaire tourne, rempli de trois personnes et de deux groupes. Le fournisseur
tourne, et ne connaît personne. Branchez-les, en lecture seule, groupes compris,
puis connectez-vous avec un compte que le fournisseur n'a jamais créé.

Un détail vous coûtera du temps si vous le laissez faire. Les deux services
tournent dans des conteneurs, et le `localhost` d'un conteneur est le sien. Le
fournisseur vous dira que la fédération est active, et n'importera personne,
sans un seul message d'erreur.
