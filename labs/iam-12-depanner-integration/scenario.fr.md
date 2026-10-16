# Ça marchait vendredi

Lundi matin, l'application de notes ne laisse plus entrer personne. Rien n'a
été déployé pendant le week-end. Personne n'a touché à rien, ce que tout le
monde dit et qui est généralement vrai.

Quelqu'un a touché à quelque chose, et c'était probablement un changement de
deux minutes fait avec de bonnes intentions : une URL copiée d'un environnement
de recette, une case cochée en cherchant une autre, un client désactivé pendant
un rangement. Ces changements sont invisibles dans tout historique, parce
qu'ils ont été faits dans une console.

Vous avez deux sources de vérité, et vous allez vous servir des deux.

Le fournisseur **dit** ce qui ne va pas, à l'écran, dans une phrase qui nomme
presque toujours le paramètre fautif. Personne ne la lit, parce qu'elle est
enveloppée dans une page qui annonce « We are sorry... » et qui ressemble à une
panne générique.

Le fournisseur **enregistre** aussi ce qui s'est passé. Le journal d'événements
du realm porte une ligne par tentative, avec un champ qui nomme la cause en un
mot : `invalid_redirect_uri`, `client_disabled`,
`invalid_client_credentials`. Lire ce journal est plus rapide que n'importe
quelle supposition.

Et il y a une troisième chose, qui est la raison pour laquelle ce lab est noté
comme il l'est.

Chacune de ces pannes peut être faite disparaître sans être corrigée. Élargissez
l'URI de redirection en joker et l'erreur s'en va. Désactivez PKCE et toute une
classe d'erreurs s'en va. Ouvrez l'octroi par mot de passe « juste pour
vérifier » et l'application remarche. Tout cela fait fonctionner l'application
lundi, et chacun de ces gestes laisse un trou que plus personne ne regardera.

La notation vérifie que ça marche. Puis elle vérifie, un par un, que vous n'avez
rien fait de cela.
