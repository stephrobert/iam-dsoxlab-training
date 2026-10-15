import sys
p = "/home/bob/Projets/test-astro-5/.claude/worktrees/formation-iam/src/content/docs/docs/services/identite/keycloak/configuration-as-code.mdx"
t = open(p).read()
R = [
("créer un realm, un client et un rôle ; elle ne réexplique ni la console ni les flux OIDC", "créer un **realm**, un **client** et un **rôle** ; elle ne réexplique ni la **console** ni les **flux OIDC**"),
("les fichiers sont lus,", "les **fichiers** sont lus,"),
("à l'état réel relu par l'API d'administration", "à l'**état réel** relu par l'**API d'administration**"),
("n'écrit que l'écart accepté", "n'écrit que l'**écart accepté**"),
("est l'écart entre ce que décrivent les fichiers et ce que Keycloak contient vraiment", "est l'**écart** entre ce que décrivent les **fichiers** et ce que **Keycloak** contient vraiment"),
("(cadence de détection,", "(**cadence de détection**,"),
("celui de l'organisation Keycloak", "celui de l'**organisation Keycloak**"),
("contient les secrets de clients", "contient les **secrets** de clients"),
("L'image est celle", "L'**image** est celle"),
("le port est lié", "le **port** est lié"),
("le mot de passe `admin`", "le **mot de passe** `admin`"),
("auprès du realm `master`", "auprès du **realm** `master`"),
("et le compte d'administration", "et le **compte d'administration**"),
("Exportez les quatre variables", "Exportez les quatre **variables**"),
("Seuls les arguments utiles sont écrits", "Seuls les **arguments utiles** sont écrits"),
("garde sa valeur par défaut de Keycloak", "garde sa **valeur par défaut** de Keycloak"),
("ce qui sert au garde-fou de la section", "ce qui sert au **garde-fou** de la section"),
("générez un secret aléatoire dans", "générez un **secret aléatoire** dans"),
("En production, la source est un coffre", "En production, la source est un **coffre**"),
("le refus est le comportement voulu", "le refus est le **comportement voulu**"),
("`sensitive` masque la valeur à l'écran, pas dans le `terraform.tfstate`. Ne versionnez jamais le state (`.gitignore`), et en équipe placez-le dans un backend chiffré avec verrouillage", "`sensitive` **masque la valeur** à l'écran, pas dans le `terraform.tfstate`. Ne versionnez jamais le **state** (`.gitignore`), et en équipe placez-le dans un **backend chiffré** avec **verrouillage**"),
("Ce garde-fou est réel mais **limité**", "Ce **garde-fou** est réel mais **limité**"),
("protège contre une erreur de saisie", "protège contre une **erreur de saisie**"),
("un client de service dont", "un **client de service** dont"),
("le realm, deux rôles, le groupe, l'attribution de rôle et le client. L'`apply`", "le **realm**, deux **rôles**, le **groupe**, l'attribution de rôle et le **client**. L'`apply`"),
("contient les valeurs sensibles", "contient les **valeurs sensibles**"),
("l'unique redirect URI décrit", "l'unique **redirect URI** décrit"),
("l'état réel correspond à la description", "l'**état réel** correspond à la **description**"),
("Pour le client, `valid_redirect_uris`", "Pour le **client**, `valid_redirect_uris`"),
("pour le realm, `access_token_lifespan`", "pour le **realm**, `access_token_lifespan`"),
("et la panne est l'écart", "et la panne est l'**écart**"),
("le jeton revient à `600`, la redirect URI à", "le **jeton** revient à `600`, la **redirect URI** à"),
("relève d'une décision, pas", "relève d'une **décision**, pas"),
("Piège observé", "**Piège observé**"),
("ne contient ni rôles, ni groupes, ni clients", "ne contient **ni rôles, ni groupes, ni clients**"),
("L'export documente, mais ne s'applique pas à Terraform. Pour obtenir du code, écrivez un fichier `import.tf` qui nomme les objets existants, dans un dossier qui ne contient que `versions.tf` et le fichier de verrouillage. Le méta-argument `provider = keycloak` est obligatoire", "L'**export** documente, mais ne s'applique pas à Terraform. Pour obtenir du code, écrivez un fichier `import.tf` qui nomme les objets existants, dans un **dossier** qui ne contient que `versions.tf` et le fichier de verrouillage. Le **méta-argument** `provider = keycloak` est **obligatoire**"),
("avec des dizaines d'attributs par défaut", "avec des dizaines d'**attributs par défaut**"),
("le secret n'est pas récupéré", "le **secret** n'est pas récupéré"),
("puis **retirez la ligne `provider = keycloak`**", "puis retirez la ligne `provider = keycloak`"),
("le state est alors alimenté", "le **state** est alors alimenté"),
]
for a, b in R:
    if a not in t:
        print("ABSENT:", a[:60])
    t = t.replace(a, b, 1)
open(p, "w").write(t)
