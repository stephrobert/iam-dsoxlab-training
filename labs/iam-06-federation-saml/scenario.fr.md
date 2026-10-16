# L'application qui ne parlera pas OIDC

L'entreprise partenaire exploite un outil de gestion documentaire. Il est
ancien, il fonctionne, et il survivra à tous ceux qui participent à cette
décision. Il parle SAML, et il ne parlera rien d'autre : il n'y a pas de budget
pour cela, et aucune raison.

Votre fournisseur parle SAML aussi. Celui de tout le monde le parle, parce que
des applications comme celle-là existent dans toutes les entreprises, et que ce
sont souvent les plus importantes.

Il faut donc les présenter l'un à l'autre, et la façon qu'a SAML de le faire est
un échange de **métadonnées**. Chaque côté publie un document qui dit qui il
est, où il écoute, et quel certificat signe ce qu'il envoie. Aucun des deux ne
devine quoi que ce soit de l'autre.

Puis il y a la partie dont les résumés ne parlent pas. SAML ne redirige pas un
navigateur comme OIDC le fait. Il lui remet un formulaire et le lui fait
soumettre tout seul, deux fois, et l'assertion voyage dedans. C'est pourquoi une
intégration SAML ne se dépanne pas avec une trace de redirections, et pourquoi
un navigateur fait partie du protocole plutôt que d'en être une commodité.

Ce qu'on vous donne : votre fournisseur avec un compte et un groupe, et un
second realm qui tient le rôle de l'outil du partenaire, vide. Ce que vous
faites : les deux côtés de l'échange. Le client qui émet des assertions signées,
et le fournisseur d'identité qui les consomme.

Ratez-le de la bonne façon et vous le verrez : l'outil du partenaire demandera à
votre utilisateur de saisir son propre nom. Cela veut dire que l'assertion est
arrivée, qu'elle a été acceptée, et qu'elle n'en disait pas assez.
