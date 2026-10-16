# Avant tout fournisseur, il y a un annuaire

Le fournisseur d'identité est installé et il fonctionne. Il contient exactement
un compte : l'administrateur qui l'a installé. Personne d'autre n'existe, donc
personne d'autre ne peut se connecter.

C'est l'état normal des choses, et c'est là que commence tout projet d'identité.
Un fournisseur n'invente pas les gens. Il les lit quelque part, et ce quelque
part est un annuaire.

Vous avez LLDAP qui tourne sur `idp.lab`, avec son arbre et son administrateur.
Trois personnes arrivent : Aline dans l'équipe d'exploitation, Bruno qui est à
cheval sur l'exploitation et l'audit, Chloé qui ne fait jamais que lire. Deux
groupes porteront ces rôles, et le lab suivant apprendra au fournisseur à les
lire.

Le travail a l'air de cinq minutes de LDIF, et il ne l'est pas, parce que LLDAP
est un annuaire **léger**. Il parle LDAP, il accepte certaines écritures, et il
en refuse d'autres de façons qui ne sautent pas aux yeux. L'un de ces refus
ressemble trait pour trait à un succès.

Trouvez lequel, et posez les appartenances quand même. Puis redémarrez le
conteneur et regardez à nouveau : un annuaire qui oublie n'est pas un annuaire,
et le seul moyen de le savoir est d'essayer.
