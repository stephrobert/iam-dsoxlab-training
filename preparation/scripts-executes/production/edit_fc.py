import sys
p = "/home/bob/Projets/test-astro-5/.claude/worktrees/formation-iam/src/content/docs/docs/services/identite/keycloak/production.mdx"
t = open(p, encoding="utf-8").read()
reps = [
 ("  order: 5870\n", "  order: 5865\n"),
 ("Le mode `start` choisit aussi **PostgreSQL** plutôt que **H2**, comme dans la leçon d'installation.",
  "En production, on remplace aussi la base de développement **dev-file** (H2), valeur par défaut des deux modes, par un SGBD pris en charge, ici **PostgreSQL**, comme dans la leçon d'installation."),
 ("Pour le proxy lui-même, voir le guide [Caddy](/docs/services/web/caddy/). Le schéma",
  "Pour le proxy lui-même, voir le guide [Caddy](/docs/services/web/caddy/). Le schéma"),
 ("Bloquer `/realms/master/` ne casse pas la connexion à la console, dont",
  "Bloquer `/realms/master/` côté public ne devrait pas casser la connexion à la console, dont"),
 ("(`invalid_grant`, `Invalid user credentials`)", "(HTTP 400)"),
 ("signe que la table de découverte du cluster est copiée avec la base.",
  "signe probable que la table de découverte du cluster est copiée avec la base."),
 ("les API qui mettent le JWKS en cache continuent de servir tant que les jetons vivent, d'où l'intérêt d'un **access token court** ; les utilisateurs déjà connectés sont coupés à l'expiration de leur jeton. Réduire cette fenêtre demande de la **haute disponibilité** et d'une **base répliquée** (plusieurs nœuds et base répliquée), traitée dans",
  "les API qui mettent le **JWKS** en cache continuent de servir tant que les jetons vivent, d'où l'intérêt d'un **access token court** (5 à 15 minutes, fourchette de ce site) ; les utilisateurs déjà connectés perdent leur accès aux API à l'expiration de leur jeton, faute de renouvellement possible. Éviter que la panne les atteigne demande de la **haute disponibilité** (plusieurs nœuds et une base répliquée), traitée dans"),
 ("<Schema id=\"identite/keycloak-production-chemins\"",
  "La documentation du hostname précise que `KC_HOSTNAME_ADMIN` **n'interdit pas** l'accès à l'**API d'administration** par l'URL publique : c'est au **proxy** de la restreindre, ce que font les `403` du `Caddyfile` ci-dessus.\n\n<Schema id=\"identite/keycloak-production-chemins\""),
]
for a,b in reps:
    assert t.count(a)==1, a[:40]
    t = t.replace(a,b)
open(p,"w",encoding="utf-8").write(t)
q = "/tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-production/quiz-production.json"
s = open(q, encoding="utf-8").read()
a = "**KC_PROXY_HEADERS=xforwarded** fait croire les en-têtes du proxy, ce qui fixe un issuer en https."
b = "**KC_PROXY_HEADERS=xforwarded** fait faire confiance aux en-têtes du proxy, et c'est **KC_HOSTNAME** en URL complète qui fixe un issuer en https."
assert s.count(a)==1
open(q,"w",encoding="utf-8").write(s.replace(a,b))
