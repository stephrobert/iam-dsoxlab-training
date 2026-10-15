source /tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-mfa/env.sh
set -x
kcadm update realms/lab -s 'passwordPolicy=length(15) and notUsername'
kcadm get realms/lab --fields passwordPolicy
kcadm create groups -r lab -s name=devops
kcadm create groups -r lab -s name=lecteurs
kcadm create roles -r lab -s name=mfa-requis -s 'description=Second facteur obligatoire'
kcadm add-roles -r lab --gname devops --rolename mfa-requis
for u in alice:devops bruno:lecteurs; do
  n=${u%%:*}; g=${u##*:}
  kcadm create users -r lab -s username=$n -s enabled=true -s firstName=$n -s lastName=Lab -s email=$n@exemple.fr
  kcadm set-password -r lab --username $n --new-password 'phrase-de-passe-longue-2026'
  GID=$(kcadm get groups -r lab -q search=$g --fields id --format csv --noquotes)
  UID_=$(kcadm get users -r lab -q username=$n --fields id --format csv --noquotes)
  kcadm update users/$UID_/groups/$GID -r lab -s realm=lab -s userId=$UID_ -s groupId=$GID -n
done
kcadm get users -r lab --fields username,requiredActions
kcadm get authentication/config-description/conditional-user-role -r lab
