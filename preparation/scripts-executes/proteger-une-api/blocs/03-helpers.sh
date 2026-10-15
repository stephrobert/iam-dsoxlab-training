KC=http://localhost:8080/realms/lab/protocol/openid-connect
dec() {
  local s; s=$(cut -d. -f2 <<<"$1" | tr '_-' '/+')
  while [ $(( ${#s} % 4 )) -ne 0 ]; do s="$s="; done
  base64 -d <<<"$s"
}
alice() {
  curl -s -X POST "$KC/token" -d grant_type=password -d client_id=notes-cli \
    -d username=alice -d password='Alice-lab-2026' "$@" | jq -r .access_token
}
SANS=$(alice)
AVEC=$(alice -d scope=notes:lecture)
dec "$SANS" | jq -c '{iss, aud, azp, scope}'
dec "$AVEC" | jq -c '{iss, aud, azp, scope}'
