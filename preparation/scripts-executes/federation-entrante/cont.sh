#!/usr/bin/env bash
# usage: cont.sh champ=valeur ... ; répond au formulaire de last-page.html avec le jar last-jar.txt
A=$(grep -o 'action="[^"]*"' last-page.html | head -1 | sed 's/action="//;s/"$//;s/&amp;/\&/g')
args=(); for kv in "$@"; do args+=(--data-urlencode "$kv"); done
code=$(curl -s -o next.html -D next.h -w '%{http_code}' -b last-jar.txt -c last-jar.txt "${args[@]}" "$A")
echo "POST $code"
loc=$(grep -i '^location:' next.h | tr -d '\r' | cut -d' ' -f2-)
while [ -n "$loc" ]; do
  case $loc in http://localhost:9999/*) echo "RETOUR APPLI: ${loc%%\?*}"; break;; esac
  code=$(curl -s -o next.html -D next.h -w '%{http_code}' -b last-jar.txt -c last-jar.txt "$loc")
  echo "GET $code ${loc%%\?*}"
  loc=$(grep -i '^location:' next.h | tr -d '\r' | cut -d' ' -f2-)
done
grep -o 'kc-feedback-text">[^<]*' next.html | sed 's/.*">/message: /'
grep -o 'kc-error-message[^<]*<[^<]*' next.html | head -2
grep -o '<button[^>]*>[^<]*' next.html | sed 's/class="[^"]*"//' | head
grep -o 'name="[a-zA-Z_]*"' next.html | sort -u | tr '\n' ' '; echo
cp next.html last-page.html
