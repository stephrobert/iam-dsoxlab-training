# Tutorial: three mechanisms to see at work

This tutorial does not do the challenge. It shows you the three mechanisms the
challenge needs, at work, on the partner that is already running and on a
throwaway group. Nothing here declares the identity provider.

Read the lab's details first:

```bash
cat /opt/iam-lab/identifiants-lab.txt
```

## 1. What the partner publishes, and what it does not

A partner you federate with hands you three things: a discovery URL, a client
identifier, and a secret. Everything else, you read:

```bash
DEC=$(grep '^DECOUVERTE_PARTENAIRE=' /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)
curl -s "$DEC" | jq '{issuer, authorization_endpoint, token_endpoint,
                      userinfo_endpoint, jwks_uri}'
```

Five addresses, all derived from one URL. Typing them by hand is how a
federation breaks the day the partner moves something.

Now look at the keys, which is the part worth understanding:

```bash
JWKS=$(curl -s "$DEC" | jq -r .jwks_uri)
curl -s "$JWKS" | jq '{nombre: (.keys | length),
                       ids: [.keys[].kid], usages: [.keys[].use]}'
```

Several keys, each with an identifier. A provider rotates them: it publishes a
new one, signs with it, and keeps the old one around long enough for tokens in
flight. If your broker **reads** this address, it follows that rotation without
anyone doing anything. If someone pasted a key into a field instead, the
federation works until the rotation, and then stops, on a day when nobody has
changed anything.

## 2. A default group belongs to the realm

Create a throwaway group and watch what it does on its own:

```bash
KC=http://127.0.0.1:8080
U=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME=' /opt/socle-iam/.env | cut -d= -f2-)
P=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD=' /opt/socle-iam/.env | cut -d= -f2-)
ADM=$(curl -s -X POST "$KC/realms/master/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  -d "username=$U" -d "password=$P" | jq -r .access_token)

curl -s -o /dev/null -w 'groupe : HTTP %{http_code}\n' -X POST \
  "$KC/admin/realms/formation/groups" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d '{"name":"demo-tuto"}'

echo "les groupes par defaut du realm :"
curl -s "$KC/admin/realms/formation/default-groups" \
  -H "Authorization: Bearer $ADM" | jq -c '[.[].name]'
```

An empty list. The group exists and the realm does not know it should be used.
Create an account now and look:

```bash
curl -s -o /dev/null -X POST "$KC/admin/realms/formation/users" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d '{"username":"demo-avant","enabled":true}'
ID=$(curl -s "$KC/admin/realms/formation/users?username=demo-avant&exact=true" \
  -H "Authorization: Bearer $ADM" | jq -r '.[0].id')
curl -s "$KC/admin/realms/formation/users/$ID/groups" \
  -H "Authorization: Bearer $ADM" | jq -c '[.[].name]'
```

Nothing. Now tell the realm, and create a second account:

```bash
GID=$(curl -s "$KC/admin/realms/formation/groups" \
  -H "Authorization: Bearer $ADM" \
  | jq -r '.[] | select(.name=="demo-tuto") | .id')
curl -s -o /dev/null -w 'default-groups : HTTP %{http_code}\n' -X PUT \
  "$KC/admin/realms/formation/default-groups/$GID" \
  -H "Authorization: Bearer $ADM"

curl -s -o /dev/null -X POST "$KC/admin/realms/formation/users" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d '{"username":"demo-apres","enabled":true}'
ID2=$(curl -s "$KC/admin/realms/formation/users?username=demo-apres&exact=true" \
  -H "Authorization: Bearer $ADM" | jq -r '.[0].id')
echo "le compte cree APRES :"
curl -s "$KC/admin/realms/formation/users/$ID2/groups" \
  -H "Authorization: Bearer $ADM" | jq -c '[.[].name]'
echo "et le compte cree AVANT, relu :"
curl -s "$KC/admin/realms/formation/users/$ID/groups" \
  -H "Authorization: Bearer $ADM" | jq -c '[.[].name]'
```

The second account is in the group. The first one is still outside, and it will
stay outside: a default group applies **at creation**, and declaring it later
changes nothing for accounts that already exist.

That is worth remembering, because it is exactly what happens when you debug
this. You sign in, the account has no group, you add the default group, you sign
in again, and the account still has no group, because it is the same account.
Delete it and sign in afresh.

Clean up:

```bash
for n in demo-avant demo-apres; do
  I=$(curl -s "$KC/admin/realms/formation/users?username=$n&exact=true" \
    -H "Authorization: Bearer $ADM" | jq -r '.[0].id')
  curl -s -o /dev/null -X DELETE "$KC/admin/realms/formation/users/$I" \
    -H "Authorization: Bearer $ADM"
done
curl -s -o /dev/null -X DELETE \
  "$KC/admin/realms/formation/default-groups/$GID" -H "Authorization: Bearer $ADM"
curl -s -o /dev/null -X DELETE "$KC/admin/realms/formation/groups/$GID" \
  -H "Authorization: Bearer $ADM"
echo "nettoye"
```

## 3. What the first-login flow actually does

A flow is a list of steps. Read the one Keycloak gives you for an account
arriving from outside for the first time:

```bash
curl -s "$KC/admin/realms/formation/authentication/flows/first%20broker%20login/executions" \
  -H "Authorization: Bearer $ADM" \
  | jq -r '.[] | "\(.requirement)\t\(.providerId // "-")\t\(.displayName)"' \
  | head -10
```

Read the first four lines as a decision.

`idp-create-user-if-unique` creates the account when nothing matches. It is
`ALTERNATIVE`, which means: try this, and if it does not apply, try the next
thing.

The next thing is `Handle Existing Account`, and underneath it sits
`idp-confirm-link`, `REQUIRED`, followed by verification options. In other
words: an address that already exists does **not** produce a link. It produces
a question, and then a proof.

This is the part of the challenge that asks you to do nothing. There is a
provider named `idp-auto-link` which skips all of it, and its only effect is to
hand a stranger whichever local account happens to share their email address.
Knowing that it exists, and leaving it alone, is the work.

You will see the refusal when you grade: one of the partner's two accounts
stops on a screen that names the conflict. That screen is the proof.

## What the challenge asks now

You have seen that a partner publishes everything but its secret, that a
default group is a property of the realm and applies at creation, and that the
first-login flow asks a question where a careless one would hand over an
account.

The challenge asks for the identity provider, the default group, and a
first-login flow you have not weakened.

```bash
dsoxlab check iam-11-federation-externe   # grade
dsoxlab hint  iam-11-federation-externe   # one hint, at the cost of points
```
