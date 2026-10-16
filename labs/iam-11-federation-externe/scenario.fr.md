# Quinze consultants, et aucun compte pour eux

L'entreprise partenaire envoie quinze consultants pour six mois. Il leur faut
l'accès à trois de vos applications, et ils ont déjà des comptes : chez leur
propre employeur, qui gère leurs mots de passe, leurs seconds facteurs et,
surtout, leurs départs.

Vous pourriez créer quinze comptes. Tout le monde le fait, la première fois.
Puis quelqu'un quitte l'entreprise partenaire en mars, personne ne vous le dit,
et son compte fonctionne jusqu'au jour où quelqu'un pense à poser la question.

L'autre voie est de laisser leur employeur répondre pour eux. Votre realm
devient un **courtier** : quand un consultant se connecte, il l'envoie chez le
partenaire, le partenaire l'authentifie, et votre realm crée un compte local
rattaché à cette réponse. Le mot de passe ne vient jamais chez vous, et le jour
où le consultant quitte le partenaire, le refus du partenaire est votre refus.

Cette partie est simple, et ce n'est pas là que passe l'après-midi.

L'après-midi passe dans la question que personne ne pose à voix haute : **que
reçoit exactement un inconnu en arrivant ?** Un compte sans groupe n'a aucun
droit et ne sert à rien. Un compte rangé à la main a ce dont la personne qui
l'a rangé s'est souvenue. Et un compte qui arrive avec un rôle
d'administration est une porte que plus personne ne regardera.

Il y a encore une chose, et c'est le tranchant de tout ce lab. Votre realm
contient déjà un compte qui porte la même adresse qu'une des personnes du
partenaire. Les adresses se télescopent : les gens changent d'employeur, des
sociétés fusionnent, quelqu'un a mal saisi quelque chose en 2019. Si votre flux
de premier login traite une adresse qui correspond comme une preuve d'identité,
alors l'inconnu du partenaire est désormais cette personne. Aucune alerte,
aucune trace, rien à remarquer.

Deux personnes du partenaire se connecteront pendant la notation. L'une doit
entrer. L'autre, non.
