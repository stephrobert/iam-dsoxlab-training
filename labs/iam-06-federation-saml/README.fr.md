# Tutoriel : trois mécanismes à voir fonctionner

Ce tutoriel ne fait pas le challenge. Il vous montre à l'œuvre les trois
mécanismes sur lesquels SAML repose, en lisant ce que les deux realms publient
déjà sur eux-mêmes. Rien ici ne déclare le client ni le fournisseur d'identité.

Lisez d'abord les coordonnées du lab :

```bash
cat /opt/iam-lab/identifiants-lab.txt
```

## 1. Les métadonnées : personne ne devine rien

Un fournisseur OIDC publie un document JSON. Un fournisseur SAML publie du XML,
à une adresse fixe, et il contient tout ce dont l'autre côté a besoin :

```bash
KC=http://127.0.0.1:8080
curl -s "$KC/realms/formation/protocol/saml/descriptor" \
  | head -c 700; echo
```

Trois choses s'y trouvent, et chacune répond à un champ que vous aurez à
remplir.

L'**identifiant d'entité**, qui est ce que l'émetteur prétend être :

```bash
curl -s "$KC/realms/formation/protocol/saml/descriptor" \
  | grep -oE 'entityID="[^"]+"'
```

L'**adresse de connexion**, où le navigateur est envoyé :

```bash
curl -s "$KC/realms/formation/protocol/saml/descriptor" \
  | grep -oE 'SingleSignOnService[^>]*Location="[^"]+"' | head -2
```

Et le **certificat** qui signe ce que l'émetteur envoie :

```bash
CERT=$(curl -s "$KC/realms/formation/protocol/saml/descriptor" \
  | grep -oE '<ds:X509Certificate>[^<]+' | head -1 | sed 's/.*>//')
echo "longueur : ${#CERT}"
echo "$CERT" | head -c 60; echo "..."
```

Regardez ce qu'est vraiment ce certificat, en le décodant :

```bash
printf -- '-----BEGIN CERTIFICATE-----\n%s\n-----END CERTIFICATE-----\n' "$CERT" \
  | openssl x509 -noout -subject -issuer -dates
```

Un certificat auto-signé appartenant au realm. Le consommateur fera confiance
aux assertions **parce qu'elles** portent une signature qu'il peut vérifier
contre celui-ci. Copiez-le d'ailleurs et rien ne se vérifiera.

## 2. L'adresse qui découle d'un nom

Le consommateur a une adresse où il reçoit les assertions, et cette adresse
n'est pas libre. Elle est construite à partir du realm et de l'**alias** du
fournisseur d'identité :

```bash
grep -E '^(ENTITE|ACS|ALIAS)' /opt/iam-lab/identifiants-lab.txt
```

Lisez-la avec attention :
`.../realms/partenaire-sp/broker/saml-formation/endpoint`. Le `saml-formation`
au milieu est l'alias. Nommez le fournisseur d'identité autrement et cette
adresse change, le client de l'émetteur déclare la mauvaise, et l'assertion part
là où personne n'écoute.

Cette adresse n'existe pas encore, puisque le fournisseur d'identité n'existe
pas encore :

```bash
curl -s -o /dev/null -w 'ACS : HTTP %{http_code}\n' \
  "$KC/realms/partenaire-sp/broker/saml-formation/endpoint"
```

Et les métadonnées du consommateur, qu'on donnerait normalement à un émetteur,
n'ont rien à publier non plus :

```bash
curl -s -o /dev/null -w 'metadonnees du consommateur : HTTP %{http_code}\n' \
  "$KC/realms/partenaire-sp/broker/saml-formation/endpoint/descriptor"
```

C'est la poule et l'œuf de SAML, et c'est pourquoi l'alias est imposé par ce
challenge : il faut connaître l'adresse avant que la chose qui la sert existe.

## 3. Comment une assertion traverse un navigateur

OIDC déplace un navigateur avec des redirections HTTP. SAML, non. Il remet au
navigateur un formulaire qui contient l'assertion, et le fait soumettre par du
JavaScript.

Vous pouvez voir la différence sans rien configurer, du côté OIDC qui est déjà
en place. Regardez ce que fait l'application témoin :

```bash
curl -s -o /dev/null -w 'connexion : HTTP %{http_code}, vers %{redirect_url}\n' \
  http://127.0.0.1:9080/connexion
```

Un `302`, et une destination dans l'en-tête. C'est une redirection : une ligne,
visible dans n'importe quelle trace.

Regardez maintenant l'outil dont les tests se servent, et ce qu'il a fallu lui
apprendre pour suivre SAML :

```bash
grep -A6 'auto-soumis' /opt/iam-lab/outils/parcours.py | head -20
```

Il cherche un formulaire dont la méthode est `post`, qui porte des champs
cachés, et dont la page appelle `.submit()`. Puis il le poste lui-même. Sans
cela, un parcours SAML s'arrête au premier de ces formulaires, et la trace ne
montre rien d'anormal : la dernière réponse était un `200` parfaitement
ordinaire.

Cela vaut d'être compris avant de dépanner quoi que ce soit, parce que cela
change l'endroit où l'on regarde. Une intégration SAML n'échoue pas dans une
chaîne de redirections. Elle échoue dans le contenu d'un formulaire, ou dans la
signature de ce que ce formulaire transporte.

Quand vous aurez bâti les deux côtés, vous verrez le parcours complet. Il fait
huit étapes, dont deux de ces formulaires auto-soumis, et les tests les
affichent quand ils échouent.

## Ce que le challenge demande maintenant

Vous avez vu que chaque côté publie tout ce dont l'autre a besoin, que l'adresse
du consommateur découle d'un alias que vous choisissez, et que l'assertion
voyage dans des formulaires plutôt que dans des redirections.

Le challenge demande le client qui signe, le fournisseur d'identité qui vérifie,
les attributs qui doivent passer, et le groupe qui doit suivre.

```bash
dsoxlab check iam-06-federation-saml   # noter
dsoxlab hint  iam-06-federation-saml   # un indice, au prix de quelques points
```
