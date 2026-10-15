#!/usr/bin/env bash
# usage: login.sh <utilisateur partenaire> <mot de passe> [hint=oui|non]
# Rejoue la connexion navigateur avec curl et un fichier de cookies.
set -u
USER_P=$1; PASS_P=$2; HINT=${3:-oui}
JAR=$(mktemp)
BASE=http://localhost:8080/realms/lab/protocol/openid-connect
URL="$BASE/auth?client_id=app-interne&response_type=code&scope=openid&redirect_uri=http://localhost:9999/cb&state=abc"
[ "$HINT" = oui ] && URL="$URL&kc_idp_hint=partenaire"
PAGE=$(mktemp)

# suit les redirections à la main, s'arrête sur une page HTML ou sur le retour vers l'application
suivre() {
  local url=$1 code loc
  while :; do
    code=$(curl -s -o "$PAGE" -D "$PAGE.h" -w '%{http_code}' -b "$JAR" -c "$JAR" "$url")
    echo "GET  $code  ${url%%\?*}" >&2
    loc=$(grep -i '^location:' "$PAGE.h" | tr -d '\r' | cut -d' ' -f2-)
    [ -z "$loc" ] && return 0
    case $loc in
      http://localhost:9999/*) echo "RETOUR APPLI: ${loc%%\?*}?$(echo "${loc#*\?}" | sed 's/code=[^&]*/code=<code>/')" >&2; FINAL=$loc; return 0;; esac
    url=$loc
  done
}
action() { grep -o 'action="[^"]*"' "$PAGE" | head -1 | sed 's/action="//;s/"$//;s/&amp;/\&/g'; }

FINAL=
suivre "$URL"
echo "page: $(grep -o '<title>[^<]*' "$PAGE" | sed 's/<title>//' | tr -s ' \n' ' ')" >&2
if [ "$HINT" = non ]; then
  echo "liens IdP: $(grep -o 'id="social-[a-z]*"' "$PAGE" | tr '\n' ' ')" >&2
  A=$(grep -o 'href="[^"]*/broker/partenaire/login[^"]*"' "$PAGE" | head -1 | sed 's/href="//;s/"$//;s/&amp;/\&/g')
  suivre "http://localhost:8080${A#http://localhost:8080}"
fi
# formulaire du partenaire
A=$(action)
code=$(curl -s -o "$PAGE" -D "$PAGE.h" -w '%{http_code}' -b "$JAR" -c "$JAR" --data-urlencode "username=$USER_P" --data-urlencode "password=$PASS_P" "$A")
echo "POST $code  (formulaire partenaire)" >&2
loc=$(grep -i '^location:' "$PAGE.h" | tr -d '\r' | cut -d' ' -f2-)
[ -n "$loc" ] && suivre "$loc"
echo "page: $(grep -o '<title>[^<]*' "$PAGE" | sed 's/<title>//' | tr -s ' \n' ' ')" >&2
# écrans éventuels du premier login : on les affiche puis on répond
n=0
while [ -z "$FINAL" ] && [ $n -lt 4 ]; do
  n=$((n+1))
  A=$(action)
  echo "formulaire: $A" | sed 's/session_code=[^&]*/session_code=<..>/;s/tab_id=[^&]*/tab_id=<..>/' >&2
  echo "champs: $(grep -o 'name="[^"]*"' "$PAGE" | tr '\n' ' ')" >&2
  grep -o 'kc-feedback-text[^<]*<' "$PAGE" >&2 || true
  grep -o 'id="kc-error-message"[^/]*/p>' "$PAGE" >&2 || true
  break
done
echo "$FINAL" > "$PAGE.final"
cp "$PAGE" last-page.html
cp "$JAR" last-jar.txt
echo "$FINAL" > last-final.txt
