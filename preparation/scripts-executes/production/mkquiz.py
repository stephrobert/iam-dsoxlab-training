import json
U = "/docs/services/identite/keycloak/production/"
L = "intermediaire"
S = {
 1: "Comment placer Keycloak derrière un reverse proxy TLS ?",
 2: "Comment restreindre la console d'administration ?",
 3: "Où sont la santé et les métriques ?",
 4: "Que sauvegarder, et pourquoi l'export de realm ne suffit pas ?",
 5: "Comment monter de la 26.7.0 à la 26.8.1 ?",
 6: "Comment retrouver un accès administrateur perdu ?",
 7: "Que se passe-t-il quand Keycloak tombe ?",
}
def q(i, intitule, choix, rep, expl):
    return {"type": "qcm", "intitule": intitule, "choix": choix, "reponse": rep, "explication": expl,
            "section": S[i], "url": U, "level": L}
Q = [
 q(1, "Quelles options faut-il pour faire tourner Keycloak 26 en mode start derrière un proxy qui termine TLS ?",
   ["KC_HOSTNAME en URL complète, KC_HTTP_ENABLED=true et KC_PROXY_HEADERS=xforwarded",
    "KC_HOSTNAME_STRICT=false seul, le proxy se chargeant du reste",
    "KC_HTTP_ENABLED=false et un certificat déposé dans Keycloak",
    "La commande start-dev, qui active tout automatiquement"],
   "KC_HOSTNAME en URL complète, KC_HTTP_ENABLED=true et KC_PROXY_HEADERS=xforwarded",
   "Le mode **start** refuse de démarrer sans **KC_HOSTNAME** ni choix TLS ou HTTP. Derrière un proxy qui termine TLS, **KC_HTTP_ENABLED=true** autorise le HTTP interne et **KC_PROXY_HEADERS=xforwarded** fait croire les en-têtes du proxy, ce qui fixe un issuer en https."),
 q(2, "Que recommande la documentation de Keycloak pour les chemins exposés sur Internet ?",
   ["Exposer /realms/, /resources/ et /.well-known/, garder /admin/ et /realms/master/ en interne",
    "Exposer tous les chemins, le mot de passe de l'administrateur suffit à protéger la console, même depuis Internet",
    "Exposer uniquement /admin/ pour que les applications puissent se connecter",
    "Exposer /metrics et /health pour permettre une supervision depuis l'extérieur"],
   "Exposer /realms/, /resources/ et /.well-known/, garder /admin/ et /realms/master/ en interne",
   "La documentation du **reverse proxy** liste ces trois chemins comme nécessaires aux applications et garde **/admin/**, **/realms/master/**, **/metrics** et **/health** en interne. Dans le lab, tout chemin non listé reçoit un **403** sur l'adresse publique."),
 q(3, "Où répondent /health/ready et /metrics, et comment les joindre sans les exposer ?",
   ["Sur le port 8080, derrière le proxy public protégé par un mot de passe",
    "Sur le port 9000, atteint par le réseau interne sans publier ce port",
    "Sur le port 8443, après avoir activé le TLS directement dans Keycloak lui-même",
    "Sur le port 80 du proxy, avec un filtrage par l'en-tête Host"],
   "Sur le port 9000, atteint par le réseau interne sans publier ce port",
   "Avec **KC_HEALTH_ENABLED** et **KC_METRICS_ENABLED**, ces endpoints vivent sur le **port de gestion 9000**. Sur le 8080 ils répondent **404**, et la documentation précise qu'on ne proxifie pas le 9000 : la supervision le joint par le réseau interne."),
 q(4, "Que ne contient pas un export produit par kc.sh export ?",
   ["Les sessions et les événements",
    "Les clients du realm avec leurs rôles et leurs scopes",
    "Les utilisateurs du realm avec leurs mots de passe hachés",
    "Les clés de signature et la configuration du realm"],
   "Les sessions et les événements",
   "La documentation de l'export précise qu'il n'inclut **ni événements, ni sessions persistées**, ni jetons révoqués. En revanche le fichier contient les clients, les utilisateurs avec leurs **secrets hachés** et les **clés privées** du realm, donc il se protège comme un secret."),
 q(5, "Que faire avant de remplacer l'image 26.7.0 par la 26.8.1 ?",
   ["Rien : la migration du schéma se défait simplement en relançant l'ancienne image",
    "Arrêter Keycloak et sauvegarder la base, faute de retour arrière possible",
    "Exporter le realm au format JSON, ce qui suffit ensuite à revenir en arrière",
    "Supprimer le volume PostgreSQL pour repartir d'une base propre"],
   "Arrêter Keycloak et sauvegarder la base, faute de retour arrière possible",
   "Le schéma migré n'est **plus compatible** avec l'ancienne version et Keycloak ne gère pas le retour arrière : on sauvegarde la base **serveur arrêté**. Lancer la 26.7.0 sur une base migrée ne produit qu'un **avertissement**, pas une protection."),
 q(6, "Comment recréer un administrateur dans le realm master quand le compte est perdu ?",
   ["Relancer en start-dev sur la même base pour réinitialiser le mot de passe",
    "Serveur arrêté, kc.sh bootstrap-admin user avec les mêmes options de base",
    "Changer KC_BOOTSTRAP_ADMIN_PASSWORD, relu à chaque démarrage du serveur Keycloak par la suite",
    "Supprimer le realm master puis importer un export de realm"],
   "Serveur arrêté, kc.sh bootstrap-admin user avec les mêmes options de base",
   "Les variables **KC_BOOTSTRAP_ADMIN_*** ne servent qu'à la création du realm master. Pour un compte perdu, la documentation prévoit **kc.sh bootstrap-admin user**, nœuds arrêtés et avec les mêmes options de base de données ; le compte créé est **temporaire** et se remplace par un compte nominatif."),
 {"type": "vf", "intitule": "Quand Keycloak est arrêté, un jeton d'accès déjà émis reste vérifiable jusqu'à son exp par une API qui garde une copie du JWKS.",
  "reponse": "Vrai",
  "explication": "La signature se vérifie **hors ligne** avec les clés publiques en copie : le jeton est valide jusqu'à **exp**. En revanche, **nouvelles connexions** et **renouvellements** par refresh token échouent tant que l'IdP est arrêté (502 observé au proxy).",
  "section": S[7], "url": U, "level": L},
 {"type": "vf", "intitule": "Un export de realm obtenu avec kc.sh export suffit comme sauvegarde complète d'un Keycloak.",
  "reponse": "Faux",
  "explication": "L'export ne porte **ni sessions, ni événements**, ni le realm master, et n'est cohérent que serveur arrêté. La sauvegarde de référence est le **pg_dump** de la base, dont la restauration a permis d'accepter un refresh token pris avant la sauvegarde.",
  "section": S[4], "url": U, "level": L},
]
rangs = []
for x in Q:
    if x["type"] == "qcm":
        ls = sorted((len(c) for c in x["choix"]), reverse=True)
        rangs.append(ls.index(len(x["reponse"])) + 1)
        assert x["reponse"] in x["choix"]
    assert len(x["explication"]) >= 120
print("rangs", rangs)
json.dump({"keycloak-production": Q}, open("/tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-production/quiz-production.json", "w"), ensure_ascii=False, indent=1)
