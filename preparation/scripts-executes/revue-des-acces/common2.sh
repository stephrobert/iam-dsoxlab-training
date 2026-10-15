source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/lab-revue/common.sh
tok() {
  curl -s -X POST $KC/realms/entreprise/protocol/openid-connect/token \
    -d grant_type=client_credentials -d client_id=scim-client \
    --data-urlencode "client_secret@.scim-secret" | jq -r .access_token
}
T=$(tok)
J=(-H "Authorization: Bearer $T" -H "Content-Type: application/scim+json" -H "Accept: application/scim+json")
SCH_GROUPE='urn:ietf:params:scim:schemas:core:2.0:Group'
SCH_USER='urn:ietf:params:scim:schemas:core:2.0:User'
