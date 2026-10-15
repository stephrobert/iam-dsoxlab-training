#!/usr/bin/env bash
source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/lab-revue/common2.sh
source vars.sh
for r in lecture-compta acces-dev acces-prod; do kcadm create roles -r entreprise -s name=$r; done
kcadm add-roles -r entreprise --gname compta --rolename lecture-compta
kcadm add-roles -r entreprise --gname dev --rolename acces-dev
kcadm add-roles -r entreprise --uusername claire.dubois --rolename acces-prod
curl -s -X POST $SC/Users "${J[@]}" -d "{\"schemas\":[\"$SCH_USER\"],\"userName\":\"sophie.martin\",
  \"name\":{\"givenName\":\"Sophie\",\"familyName\":\"Martin\"},
  \"emails\":[{\"value\":\"sophie.martin@exemple.fr\",\"type\":\"work\",\"primary\":true}],
  \"active\":true,\"groups\":[{\"value\":\"$COMPTA\"}]}" | jq -r .id
kcadm add-roles -r entreprise --uusername sophie.martin --rolename acces-prod
echo "== workflow en cours pour sophie ? mails/groups"
exporter() {
  echo "compte,actif,groupes,roles_via_groupes,roles_directs"
  kcadm get users -r entreprise --fields id,username,enabled \
    | jq -c '.[] | select(.username | startswith("service-account-") | not)' |
  while read -r u; do
    id=$(jq -r .id <<<"$u")
    groupes=$(kcadm get "users/$id/groups" -r entreprise)
    via=""
    for g in $(jq -r '.[].id' <<<"$groupes"); do
      via="$via $(kcadm get "groups/$g/role-mappings/realm" -r entreprise | jq -r '.[].name')"
    done
    direct=$(kcadm get "users/$id/role-mappings/realm" -r entreprise \
      | jq -r '[.[].name | select(startswith("default-roles-") | not)] | join(" ")')
    jq -r --arg g "$(jq -r '[.[].name] | join(" ")' <<<"$groupes")" --arg v "$(echo $via)" --arg d "$direct" \
      '[.username, .enabled, $g, $v, $d] | @csv' <<<"$u"
  done
}
exporter | tee revue-avant.csv
awk -F',' 'NR>1 && $5!="\"\""' revue-avant.csv
echo "== apres retrait"
kcadm remove-roles -r entreprise --uusername sophie.martin --rolename acces-prod
exporter > revue-apres.csv
diff revue-avant.csv revue-apres.csv
