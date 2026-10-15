# source ce fichier
S=/tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-depannage
kcadm() { docker exec keycloak /opt/keycloak/bin/kcadm.sh "$@"; }
KC=http://localhost:8080/realms/lab/protocol/openid-connect
dec() { local s; s=$(cut -d. -f2 <<<"$1" | tr '_-' '/+'); while [ $(( ${#s} % 4 )) -ne 0 ]; do s="$s="; done; base64 -d <<<"$s"; }
PY=$S/../author-api/venv/bin/python
