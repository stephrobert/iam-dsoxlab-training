# Tutorial: three silences, seen on your own situation

This tutorial does not do the challenge. It shows you the three things that fail
without saying so, on the account that is leaving, before you touch anything.

Read first. Each of these three has cost someone a real audit finding.

```bash
KC=http://127.0.0.1:8080
IDS=/opt/iam-lab/identifiants-lab.txt
QUI=$(grep '^QUI_PART=' $IDS | cut -d= -f2-)
U=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME=' /opt/socle-iam/.env | cut -d= -f2-)
P=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD=' /opt/socle-iam/.env | cut -d= -f2-)
ADM=$(curl -s -X POST "$KC/realms/master/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  -d "username=$U" -d "password=$P" | jq -r .access_token)
ID=$(curl -s "$KC/admin/realms/formation/users?username=$QUI&exact=true" \
  -H "Authorization: Bearer $ADM" | jq -r '.[0].id')
echo "$QUI : $ID"
```

Look at what she has, in one place:

```bash
echo "actif  : $(curl -s "$KC/admin/realms/formation/users/$ID" \
  -H "Authorization: Bearer $ADM" | jq -r .enabled)"
echo "groupes: $(curl -s "$KC/admin/realms/formation/users/$ID/groups" \
  -H "Authorization: Bearer $ADM" | jq -c '[.[].name]')"
echo "roles  : $(curl -s "$KC/admin/realms/formation/users/$ID/role-mappings" \
  -H "Authorization: Bearer $ADM" \
  | jq -c '[.realmMappings[]?.name] | map(select(startswith("default-roles-") | not))')"
echo "session: $(curl -s "$KC/admin/realms/formation/users/$ID/sessions" \
  -H "Authorization: Bearer $ADM" | jq length)"
```

A role in that list belongs to her account directly, not to a group. Remember
it: a review built from group memberships will never show it.

## Silence 1: the session outlives the disabling

Disable her, on purpose, to see what it does and does not do:

```bash
curl -s -o /dev/null -w 'desactivation : HTTP %{http_code}\n' -X PUT \
  "$KC/admin/realms/formation/users/$ID" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d '{"enabled":false}'

echo "actif   : $(curl -s "$KC/admin/realms/formation/users/$ID" \
  -H "Authorization: Bearer $ADM" | jq -r .enabled)"
echo "sessions: $(curl -s "$KC/admin/realms/formation/users/$ID/sessions" \
  -H "Authorization: Bearer $ADM" | jq length)"
```

Disabled, and the session is still there. The account page says what you want
to read, and nothing says the session continues.

What does that session still allow? Try the refresh token the setup left:

```bash
RT=$(grep '^REFRESH_TOKEN=' /opt/iam-lab/jetons-de-la-session.txt | cut -d= -f2-)
curl -s -X POST "$KC/realms/formation/protocol/openid-connect/token" \
  -d grant_type=refresh_token -d client_id=appli-notes \
  -d "refresh_token=$RT" | jq -c '{error, error_description}'
```

Refused, with a reason. So the disabling does bite on the refresh. But look at
the **access token**, which is a different thing entirely:

```bash
AT=$(grep '^ACCESS_TOKEN=' /opt/iam-lab/jetons-de-la-session.txt | cut -d= -f2-)
echo "userinfo : $(curl -s -o /dev/null -w '%{http_code}' \
  "$KC/realms/formation/protocol/openid-connect/userinfo" \
  -H "Authorization: Bearer $AT")"

charge() {
  local c=$(echo "$1" | cut -d. -f2)
  local pad=$(( (4 - ${#c} % 4) % 4 ))
  [ "$pad" -gt 0 ] && c="$c$(printf '=%.0s' $(seq 1 "$pad"))"
  echo "$c" | tr '_-' '/+' | base64 -d
}
EXP=$(charge "$AT" | jq -r .exp)
echo "ce jeton expire dans $(( EXP - $(date +%s) )) secondes"
```

`userinfo` refuses it, because `userinfo` asks Keycloak. And the token itself is
still perfectly signed and not yet expired.

That difference is the whole point. An API that validates a token **offline**,
with the signature and the claims, the way the one in lab 05 does, has no idea
this person left. It will accept that token until `exp`. Nothing you do in this
lab shortens that window: only the token's lifetime does.

## Silence 2: the provider refuses, and it is right

Try to remove her group from the provider:

```bash
GID=$(curl -s "$KC/admin/realms/formation/users/$ID/groups" \
  -H "Authorization: Bearer $ADM" | jq -r '.[0].id')
curl -s -X DELETE "$KC/admin/realms/formation/users/$ID/groups/$GID" \
  -H "Authorization: Bearer $ADM" | jq -r '.error // "(pas de corps)"'
```

Read the message. It is not a bug and not a permission problem: the group
mapper is read only, so the directory owns that membership and the provider
will not contradict it. That is exactly what lab 3 set up, and it is what you
want.

So the removal happens in the directory, through its API:

```bash
WEB=http://127.0.0.1:17170
MDP=$(grep '^LLDAP_ADMIN_PASSWORD=' /opt/socle-iam/.env | cut -d= -f2-)
JL=$(curl -s -X POST "$WEB/auth/simple/login" \
  -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg m "$MDP" '{username:"admin", password:$m}')" | jq -r .token)
curl -s -X POST "$WEB/api/graphql" -H "Authorization: Bearer $JL" \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ groups { id displayName } }"}' | jq -c '.data.groups'
```

One warning before you use that API, and it is the third silence in disguise:
it answers HTTP `200` **with** an `errors` array when it refuses. Watching the
status code alone makes a refusal look like a success. And its `groupId` is an
**integer**: pass it as a string and you get exactly that polite refusal.

## Silence 3: the provider remembers

This one you will meet while debugging, so meet it here instead.

After removing a membership at the source, the provider still shows the old
one, even after synchronising the mapper. The synchronisation reports updated
groups, and the account keeps its group.

The provider keeps a cached view of federated accounts, and a mapper
synchronisation does not invalidate it. There is an endpoint for that, and
looking for it is part of the work.

Put her back as she was, so you start the challenge from the real situation:

```bash
curl -s -o /dev/null -w 'reactivation : HTTP %{http_code}\n' -X PUT \
  "$KC/admin/realms/formation/users/$ID" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d '{"enabled":true}'
```

The session you saw is still open, and that is fine: the challenge expects it.

## A fourth thing, about the review

The review is not paperwork. It is the only answer to the one question an audit
asks: what did this person have access to, on the day they left?

Build it from the provider, for every account, with **groups and roles**. The
roles are the part people skip, and they are the part that matters: a role
granted directly to an account appears in no group listing.

```bash
dsoxlab check iam-08-depart-collaborateur   # grade
dsoxlab hint  iam-08-depart-collaborateur   # one hint, at the cost of points
```
