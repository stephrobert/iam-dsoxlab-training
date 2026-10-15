b = "/tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-cac/quiz-configuration-as-code.json"
t = open(b).read()
R = [
 ("Son plan montre l'écart avant toute écriture et sa CI teste Keycloak 26.7 et 26.8", "Son plan montre l'écart avant d'écrire et sa CI teste Keycloak 26.7"),
 ("Parcequ", "Parcequ"),
 ("Parce que sensitive ne chiffre rien : le state contient le secret en clair", "Parce que sensitive ne chiffre rien : le state garde le secret en clair"),
 ("Le fichier de verrouillage .terraform.lock.hcl, qui liste les realms autorisés", "Le fichier de verrouillage .terraform.lock.hcl du dossier, qui liste les realms autorisés"),
]
for a, c in R:
    t = t.replace(a, c)
open(b, "w").write(t)
