docker run -d --name kc-lab3 -p 8093:8080 \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \
  -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:26.7.0@sha256:0f198be292568439d700cdbfb893e69a6009bb43a94a06a945b1d3d506c76b13 \
  start-dev
until curl -sf http://localhost:8093/realms/master >/dev/null; do sleep 2; done

kcadm() { docker exec kc-lab3 /opt/keycloak/bin/kcadm.sh "$@"; }
kcadm config credentials --server http://localhost:8080 --realm master --user admin --password admin
kcadm create realms -s realm=lab -s enabled=true
kcadm create groups -r lab -s name=devops
kcadm create groups -r lab -s name=lecteurs
kcadm create roles -r lab -s name=mfa-requis -s 'description=Second facteur obligatoire'
kcadm add-roles -r lab --gname devops --rolename mfa-requis

for u in alice:devops bruno:lecteurs; do
  n=${u%%:*}; g=${u##*:}
  kcadm create users -r lab -s username=$n -s enabled=true \
    -s firstName=$n -s lastName=Lab -s email=$n@exemple.fr
  kcadm set-password -r lab --username $n --new-password 'phrase-de-passe-longue-2026'
  GID=$(kcadm get groups -r lab -q search=$g --fields id --format csv --noquotes)
  UID_=$(kcadm get users -r lab -q username=$n --fields id --format csv --noquotes)
  kcadm update users/$UID_/groups/$GID -r lab \
    -s realm=lab -s userId=$UID_ -s groupId=$GID -n
done
