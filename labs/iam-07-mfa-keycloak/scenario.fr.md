# L'équipe qui peut enfermer tout le monde dehors

L'équipe d'exploitation a les clés de tout. Quatre personnes, chacune avec un
mot de passe, et ce mot de passe est la seule chose entre un courriel de
hameçonnage et votre production.

La décision est venue de l'audit : second facteur pour l'exploitation. Personne
n'est contre.

La façon dont cela tourne mal est presque toujours la même, et elle tourne mal
dans l'une de deux directions.

**Trop large.** Quelqu'un exige le second facteur de tout le monde, sur le flux
par défaut, et découvre lundi que le compte d'administration n'a pas de second
facteur non plus. Plus personne ne peut entrer pour revenir en arrière. Le flux
modifié était celui que Keycloak fournit, il n'y a donc rien vers quoi revenir.

**Trop étroit.** Quelqu'un l'exige avec la condition que Keycloak propose en
premier, qui s'appelle « user configured ». Elle veut dire : demander un second
facteur aux gens qui en ont un. Les quatre personnes de l'exploitation n'en ont
aucun. Elles se connectent exactement comme avant, le réglage a l'air juste dans
la console, et on annonce à l'audit que c'est fait.

Le second est le pire, parce que rien ne vous le dit. Aucune erreur, aucun
avertissement, et la console montre un flux avec le second facteur dedans.

Vous avez deux comptes, dans deux équipes, avec le même mot de passe et aucun
second facteur. L'un doit être arrêté. L'autre doit passer. C'est tout le test,
et c'est le seul qu'on ne peut pas tromper.

Pendant que vous y êtes, la politique de mot de passe mérite un regard. La
présente est celle que Keycloak livre, et la norme qu'elle devrait suivre dit
une chose qui surprend la plupart des gens : de la longueur, et rien d'autre.
Aucune règle de composition, aucune expiration.
