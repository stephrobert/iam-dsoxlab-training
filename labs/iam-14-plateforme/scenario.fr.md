# Le cluster tient sa propre liste de qui vous êtes

L'accès au cluster fonctionne par certificat. Chaque personne qui a besoin de
`kubectl` a reçu une clef et un certificat, générés une fois, par qui était
d'astreinte ce jour-là. Les fichiers ont été envoyés par messagerie. Ils
n'expirent pas dans un sens utile, et personne ne sait qui en détient une
copie.

Quand quelqu'un part, son compte d'annuaire est désactivé dans l'heure. Le
certificat continue de marcher. Il n'existe aucune liste des certificats émis,
et aucun moyen d'en révoquer un : le cluster ne consulte aucune révocation. Le
seul correctif honnête est de changer l'autorité de certification, ce qui
invalide tout le monde d'un coup, et c'est la raison pour laquelle cela n'a
jamais été fait.

Le cluster tient donc sa propre liste de qui sont les gens, et cette liste
s'écarte de l'annuaire dès l'instant où elle est écrite.

Vous allez la remplacer. On peut dire au cluster de faire confiance au
fournisseur d'identité : une personne lance `kubectl`, obtient un jeton du
fournisseur, et le cluster le lit. Le départ de l'entreprise ferme alors aussi
le cluster, parce qu'il n'y a plus qu'un seul endroit où vivent les comptes.

Deux choses doivent être vraies pour que cela vaille la peine.

Les droits doivent suivre le **groupe**, pas la personne. Si vous attachez des
droits à des noms de comptes, vous avez reconstruit l'écart ailleurs, dans un
fichier cette fois. Et le groupe doit être lié à quelque chose de **borné** :
il existe un rôle qui accorde le cluster entier, il rendrait le lab vert, et il
confierait la machine à quiconque parvient à se faire ajouter dans un groupe de
l'annuaire, ce qui n'est pas une décision que le cluster puisse examiner.

Pendant que vous y êtes, le tableau de bord de la plateforme demande le même
traitement, pour la même raison : il tient ses propres comptes locaux, et trois
d'entre eux appartiennent à des gens qui sont partis.

Un avertissement sur ce lab, qui ne concerne pas l'identité du tout. Le serveur
d'API d'un cluster refuse de faire confiance à un fournisseur en HTTP simple, et
il refuse en ne démarrant pas, avec la raison dans un journal qu'il faut aller
lire. Le setup a déjà posé un accès TLS devant le fournisseur pour que vous
puissiez travailler. Gardez en tête que le fournisseur répond maintenant sur
deux portes, et qu'il ne dit pas la même chose de lui-même sur chacune.
