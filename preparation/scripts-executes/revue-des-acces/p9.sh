#!/usr/bin/env bash
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/lab-revue/common2.sh
source vars.sh
kcadm get realms/entreprise --fields accessTokenLifespan
echo "== témoin après suppression du Workflow"
curl -s -X POST $SC/Users "${J[@]}" -d "{\"schemas\":[\"$SCH_USER\"],\"userName\":\"temoin.test\",\"name\":{\"givenName\":\"Temoin\",\"familyName\":\"Test\"},\"emails\":[{\"value\":\"temoin@exemple.fr\",\"type\":\"work\",\"primary\":true}],\"active\":true,\"groups\":[{\"value\":\"$COMPTA\"}]}" | jq -r .id
echo "== jeton expiré"
kcadm update realms/entreprise -s accessTokenLifespan=5
TE=$(tok); sleep 8
curl -s -w "\nHTTP %{http_code}\n" -H "Authorization: Bearer $TE" -H "Accept: application/scim+json" $SC/Users | tail -c 200
kcadm update realms/entreprise -s accessTokenLifespan=300
sleep 40
echo "$(date +%T) temoin: $(kcadm get users -r entreprise -q username=temoin.test --fields enabled | jq -c '.[0].enabled') $(kcadm get users -r entreprise -q username=temoin.test --fields id | jq -r '.[0].id' | xargs -I{} docker exec keycloak /opt/keycloak/bin/kcadm.sh get users/{}/groups -r entreprise | jq -c '[.[].name]')"
