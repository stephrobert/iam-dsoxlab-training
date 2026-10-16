# Tutorial: a flag that lies, and an API that answers in YAML

This tutorial does not do the challenge. It shows you three things that waste
an afternoon each, measured on this machine on 2026-10-16, on your own realm,
before you touch anything.

```bash
KC=http://127.0.0.1:8080
IDS=/opt/iam-lab/identifiants-lab.txt
REALM=$(grep '^REALM=' $IDS | cut -d= -f2-)
SCIM=$(grep '^URL_SCIM=' $IDS | cut -d= -f2-)
U=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME=' /opt/socle-iam/.env | cut -d= -f2-)
P=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD=' /opt/socle-iam/.env | cut -d= -f2-)
ADM=$(curl -s -X POST "$KC/realms/master/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  -d "username=$U" -d "password=$P" | jq -r .access_token)
echo "realm $REALM, API SCIM attendue sur $SCIM"
```

Note the `-f2-`, not `-f2`. These values contain URLs, and a URL contains `=`
nowhere but it contains `:` and `/`; the DN in another lab cost an hour to this
exact difference. `-f2` would cut at the first `=` and hand you a fragment.

## 1. The server says the feature is enabled, and the API answers 404

Look at what the server advertises, then at what it serves:

```bash
curl -s "$KC/admin/realms/$REALM" -H "Authorization: Bearer $ADM" \
  | jq '{scimApiEnabled, attributs_scim: (.attributes | with_entries(
      select(.key | test("scim"; "i"))))}'

curl -s -o /dev/null -w 'ServiceProviderConfig : HTTP %{http_code}\n' \
  "$SCIM/ServiceProviderConfig"
```

`404`. The feature is on at the server level and off on this realm, and the
flag that opens it is `scimApiEnabled`, at the **root** of the realm's
representation.

Now the part that costs the afternoon. Put it in the realm's `attributes`,
where configuration usually goes, and watch:

```bash
curl -s "$KC/admin/realms/$REALM" -H "Authorization: Bearer $ADM" \
  | jq '.attributes.scimApiEnabled = "true"' > /tmp/realm-essai.json
curl -s -o /dev/null -w 'PUT dans attributes : HTTP %{http_code}\n' -X PUT \
  "$KC/admin/realms/$REALM" -H "Authorization: Bearer $ADM" \
  -H 'Content-Type: application/json' -d @/tmp/realm-essai.json

curl -s "$KC/admin/realms/$REALM" -H "Authorization: Bearer $ADM" \
  | jq '.scimApiEnabled'
curl -s -o /dev/null -w 'et l API  : HTTP %{http_code}\n' \
  "$SCIM/ServiceProviderConfig"
```

`HTTP 204`, and the value reads back `false`. The update succeeded and changed
nothing. Nothing in the answer, nothing in the logs, nothing in the console
says the key went to a place that is never read.

This is the shape to recognise, well beyond this one flag: **an update that
returns a success code is not a state that changed.** Read the state back.

At the root, it works:

```bash
curl -s "$KC/admin/realms/$REALM" -H "Authorization: Bearer $ADM" \
  | jq '.scimApiEnabled = true' > /tmp/realm-essai.json
curl -s -o /dev/null -w 'PUT a la racine : HTTP %{http_code}\n' -X PUT \
  "$KC/admin/realms/$REALM" -H "Authorization: Bearer $ADM" \
  -H 'Content-Type: application/json' -d @/tmp/realm-essai.json

curl -s "$KC/admin/realms/$REALM" -H "Authorization: Bearer $ADM" \
  | jq '.scimApiEnabled'
curl -s -o /dev/null -w 'et l API  : HTTP %{http_code}\n' \
  "$SCIM/ServiceProviderConfig"
```

`401` instead of `404`. That is the measurement that matters: the API now
exists and is asking who you are. Keep that distinction, you will need it in
the challenge, and leave the realm as you now find it or close it again, as you
prefer: the setup closes it on every `dsoxlab run`.

## 2. Two 401, two different reasons, both in SCIM shape

Try the token you have, the realm `master` administrator's:

```bash
curl -s "$SCIM/ServiceProviderConfig" -H "Authorization: Bearer $ADM" | jq .
```

« Bearer token required ». Your token is perfectly valid and perfectly
administrative, and it is the wrong token: this API is served **by the realm**,
and it wants a token **of that realm**.

So a client of this realm, in client credentials, gives a token of the right
realm. That one gets a different message, « Invalid token audience », and the
difference is the whole lesson. The first 401 says « I do not know you ». The
second says « I know you, and this token was not issued for me ».

An audience is not a right. It is the name of the recipient, written inside the
token, and the API checks it is its own name. You gave a token an audience in
lab 05, with an audience mapper; the only question here is **which** name it
wants. Four candidates are plausible, and only one works. The ServiceProvider
URL you already have in `$SCIM` is a reasonable place to start.

## 3. The workflows API answers in YAML

The lifecycle API is the one that will disable idle accounts without anybody
being there. Ask it what it wants:

```bash
curl -s "$KC/admin/realms/$REALM/workflows" -H "Authorization: Bearer $ADM"
curl -s "$KC/admin/realms/$REALM/workflows" -H "Authorization: Bearer $ADM" \
  | jq . 2>&1 | head -2

echo "== POST vide =="
curl -s -X POST "$KC/admin/realms/$REALM/workflows" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' -d '{}'
```

« Workflow name cannot be null or empty ». And look at the listing: it
came back as `--- []`, which is **YAML**, not JSON. `jq` refuses it with
« Invalid numeric literal », and it does so on an empty realm as well as a full
one, because the `---` is there either way. Read that error as « this realm has
no workflows » and you will spend the afternoon looking for the wrong thing.

The grammar is a name and steps, each step naming what it `uses`. The verb is
the decision, not the syntax:

```text
disable-user   suspends access, keeps the account, keeps the evidence
delete-user    removes the account, and the trace of what it had
```

A review needs the second column to exist. A lifecycle rule that deletes
destroys the history of the access along with the access, unattended, at three
in the morning, and nobody will be able to answer « who had production in
March » ever again. The grading refuses `delete-user` for that reason alone.

## What this leaves you

Three habits, and they outlive this product:

- an update that returns success proves nothing: read the state back;
- `401` is not one answer, it is a family; the message says which;
- before automating a destructive verb, ask what the audit will need afterwards.

```bash
dsoxlab challenge iam-13-revue-des-acces
```
