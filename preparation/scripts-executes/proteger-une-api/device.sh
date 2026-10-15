#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")"
KC=http://localhost:8080/realms/lab/protocol/openid-connect
J=cookies.txt; : > $J
DEV=$(curl -s -X POST $KC/auth/device -d client_id=notes-cli -d scope=notes:lecture)
UC=$(jq -r .user_code <<<"$DEV"); DC=$(jq -r .device_code <<<"$DEV")
echo "user_code $UC"
curl -s -L -c $J -b $J -o p1.html "$(jq -r .verification_uri_complete <<<"$DEV")"
ACT=$(grep -o 'action="[^"]*"' p1.html | head -1 | sed 's/action="//;s/"$//;s/&amp;/\&/g')
curl -s -L -c $J -b $J -o p2.html -w 'login -> %{http_code}\n' "$ACT" -d username=alice --data-urlencode password='Alice-lab-2026'
sed 's/<[^>]*>/ /g' p2.html | tr -s ' \n' | grep -iE 'grant|access|success|accept|yes|no|consent|device|notes' | head -8
grep -o 'name="[a-z_]*" *\(value="[^"]*"\)\?' p2.html | head
echo "$ACT" > /dev/null
ACT2=$(grep -o 'action="[^"]*"' p2.html | head -1 | sed 's/action="//;s/"$//;s/&amp;/\&/g'); echo "act2 ok"; ACT2="http://localhost:8080${ACT2#http://localhost:8080}"
if [ -n "$ACT2" ]; then
  CODE=$(grep -o 'name="code" value="[^"]*"' p2.html | sed 's/.*value="//;s/"//')
  curl -s -L -c $J -b $J -o p3.html -w 'consent -> %{http_code}\n' "$ACT2" --data-urlencode "code=$CODE" -d accept=Yes
  sed 's/<[^>]*>/ /g' p3.html | tr -s ' \n' | grep -iE 'success|device|logged|granted' | head -4
fi
curl -s -X POST $KC/token -d grant_type=urn:ietf:params:oauth:grant-type:device_code -d client_id=notes-cli -d device_code=$DC | tee devtok.json | jq -c 'del(.access_token,.refresh_token)'
T=$(jq -r .access_token devtok.json)
[ "$T" != null ] && curl -s -i http://127.0.0.1:8090/notes -H "Authorization: Bearer $T" | grep -E '^HTTP'
