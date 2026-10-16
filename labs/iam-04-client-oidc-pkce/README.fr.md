# Tutoriel : trois mécanismes à voir fonctionner

Ce tutoriel ne fait pas le challenge. Il vous montre à l'œuvre les trois
mécanismes dont le challenge a besoin, sur des exemples jetables. Rien ici ne
touche au realm `formation` ni au client `appli-notes`, et c'est délibéré :
c'est à vous de reporter les idées.

Travaillez dans un répertoire temporaire :

```bash
cd "$(mktemp -d)"
```

## 1. PKCE, sans aucun serveur

On présente souvent PKCE comme une fonctionnalité de protocole. Ce sont trois
lignes d'arithmétique, et les voir dissipe le mystère.

L'application invente une chaîne au hasard, le **vérifieur**. Elle en calcule
le condensat et n'envoie que celui-ci, le **défi**, quand elle demande un code.
Plus tard, quand elle échange le code contre un jeton, elle présente le
vérifieur. Le serveur en recalcule le condensat et compare.

```bash
# Le vérifieur : au hasard, gardé par l'application, pas envoyé à ce stade.
# 48 octets et non 32 : retirer les caractères que base64url interdit raccourcit
# la chaîne, et la RFC 7636 en exige 43 au minimum. Mesuré sur 200 tirages,
# `-base64 32` est tombé trop court 144 fois, jusqu'à 37 caractères.
verifieur=$(openssl rand -base64 48 | tr -d '=+/' | cut -c1-43)
echo "vérifieur : $verifieur  (${#verifieur} caractères)"

# Le défi : son SHA-256, en base64url sans remplissage
defi=$(printf '%s' "$verifieur" | openssl dgst -binary -sha256 \
  | openssl base64 | tr '+/' '-_' | tr -d '=')
echo "défi      : $defi"
```

Voyez maintenant pourquoi cela fonctionne. Recalculez le défi depuis le même
vérifieur : vous retrouvez la même chaîne. Depuis un autre : plus rien de
commun.

```bash
printf '%s' "$verifieur" | openssl dgst -binary -sha256 \
  | openssl base64 | tr '+/' '-_' | tr -d '='
printf '%s' "autre-chaine" | openssl dgst -binary -sha256 \
  | openssl base64 | tr '+/' '-_' | tr -d '='
```

Qui vole le code d'autorisation a le code, et pas le vérifieur. Sans lui,
l'échange échoue. C'est toute la protection, et elle ne vaut que si le serveur
**exige** le vérifieur au lieu d'accepter un échange sans lui.

L'autre méthode, `plain`, envoie le vérifieur lui-même en guise de défi. Qui
peut lire l'un peut lire l'autre, et la protection disparaît. Rien ne justifie
de la choisir.

## 2. Ce qu'un realm dit de lui-même

Un fournisseur OIDC publie sa propre description à une adresse fixe. Vous n'avez
jamais à deviner un point d'accès, et jamais à deviner l'issuer.

```bash
curl -s http://127.0.0.1:8080/realms/master/.well-known/openid-configuration \
  | jq '{issuer, authorization_endpoint, token_endpoint,
         code_challenge_methods_supported, grant_types_supported}'
```

Trois choses à remarquer.

L'`issuer` est une **chaîne**, et les applications la comparent caractère par
caractère. Ce n'est pas « l'adresse du serveur » : elle porte le realm.
Lisez-la, copiez-la, ne la retapez jamais.

`code_challenge_methods_supported` liste `plain` et `S256`. Le serveur les
*prend en charge* tous les deux. Celle qu'un client donné *exige* est un
réglage de ce client, dont le document de découverte ne dit rien.

Posez la même question à un autre realm, et comparez l'`issuer` :

```bash
curl -s http://127.0.0.1:8080/realms/formation/.well-known/openid-configuration \
  | jq -r .issuer
```

Deux realms, deux issuers, le même serveur. Une application qui ne vérifierait
que la signature accepterait les jetons des deux, puisque les deux sont signés
par la même installation avec des clés parfaitement valides. C'est `iss` qui les
sépare.

## 3. Deux jetons, lus de l'intérieur

Un jeton n'est pas opaque. Sa charge est du base64url, et quiconque le détient
peut la lire. Le faire une fois change la façon de penser à ce qu'on y met, et
montre ce que la plupart des résumés énoncent de travers.

Demandez des jetons au realm `master`, avec son client d'administration, dont
l'octroi par mot de passe est ouvert :

```bash
U=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME:' /opt/socle-iam/secrets.yml | cut -d'"' -f2)
P=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD:' /opt/socle-iam/secrets.yml | cut -d'"' -f2)
REPONSE=$(curl -s -X POST \
  http://127.0.0.1:8080/realms/master/protocol/openid-connect/token \
  -d grant_type=password -d client_id=admin-cli -d scope=openid \
  -d "username=$U" -d "password=$P")
echo "$REPONSE" | jq -r 'keys | join(", ")'
```

Deux jetons reviennent, et ils ne sont pas interchangeables. Lisez les deux
charges. La fonction ci-dessous complète le remplissage base64url, dont
`base64 -d` a besoin :

```bash
charge() {
  local c=$(echo "$1" | cut -d. -f2)
  local pad=$(( (4 - ${#c} % 4) % 4 ))
  [ "$pad" -gt 0 ] && c="$c$(printf '=%.0s' $(seq 1 "$pad"))"
  echo "$c" | tr '_-' '/+' | base64 -d
}

echo "access token :"
charge "$(echo "$REPONSE" | jq -r .access_token)" | jq -r 'keys | join(", ")'
echo "ID token :"
charge "$(echo "$REPONSE" | jq -r .id_token)" | jq -r 'keys | join(", ")'
```

Mesuré sur Keycloak 26.8.1, l'access token ne porte que `azp, exp, iat, iss,
jti, scope, sid, typ`. **Ni `aud`, ni `sub`.** L'ID token, lui, porte `aud`,
`sub`, `preferred_username` et `typ: ID`.

Cela mérite qu'on s'arrête, parce que cela contredit le résumé habituel. Un
access token dit *ce qui peut être fait*, et Keycloak sait l'émettre sous une
forme allégée qui ne contient presque rien. Un ID token dit *qui s'est
connecté*, et c'est lui qu'une application valide pour connaître son
utilisateur. Demander à un access token qui est l'utilisateur peut ne rien
donner du tout.

```bash
charge "$(echo "$REPONSE" | jq -r .id_token)" | jq '{iss, aud, azp, exp, typ}'
```

Lisez `iss` : il nomme le realm, pas seulement l'hôte. Lisez `aud` : il nomme le
client à qui ce jeton est destiné. Lisez `exp` : un horodatage, après lequel il
ne vaut plus rien.

Regardez ensuite ce que vous venez de faire : vous avez lu le contenu d'un jeton
sans aucune clé. La signature le protège de la **modification**, pas de la
lecture. Rien de secret n'a sa place dans un jeton.

Et notez l'octroi dont vous vous êtes servi : `grant_type=password`, avec
l'identifiant et le mot de passe transmis tels quels. C'est commode pour un
essai, et c'est précisément ce que le challenge vous demande de fermer sur votre
propre client.

## Ce que le challenge demande maintenant

Vous avez vu que PKCE est un condensat à vérifier, qu'un realm publie son propre
issuer, et qu'un access token et un ID token ne disent pas les mêmes choses.

Le challenge vous demande d'assembler tout cela pour de vrai : donner à
l'application une identité auprès du fournisseur, exiger la preuve, déclarer
l'adresse de retour exacte, fermer ce qui doit l'être, et pointer l'application
sur le bon realm.

```bash
dsoxlab check iam-04-client-oidc-pkce   # noter
dsoxlab hint  iam-04-client-oidc-pkce   # un indice, au prix de quelques points
```
