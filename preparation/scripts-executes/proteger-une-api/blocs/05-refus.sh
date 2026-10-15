API=http://127.0.0.1:8090/notes
appel() { curl -s -i "$@" | grep -E '^HTTP|^WWW-Authenticate|^\{'; }

appel "$API"
appel "$API" -H "Authorization: Bearer $SANS"
appel "$API" -H "Authorization: Bearer $AVEC"
appel -X POST "$API" -H "Authorization: Bearer $AVEC"
COMPLET=$(alice -d 'scope=notes:lecture notes:ecriture')
appel -X POST "$API" -H "Authorization: Bearer $COMPLET"
ALTERE="${AVEC%.*}.$(cut -d. -f3 <<<"$AVEC" | tr 'A-Za-z' 'N-ZA-Mn-za-m')"
appel "$API" -H "Authorization: Bearer $ALTERE"
