# Tutorial: three mechanisms to see at work

This tutorial does not do the challenge. It shows you the three mechanisms the
challenge needs, by reading what Keycloak already offers and by making a
throwaway copy that you delete at the end.

```bash
KC=http://127.0.0.1:8080
U=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME=' /opt/socle-iam/.env | cut -d= -f2-)
P=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD=' /opt/socle-iam/.env | cut -d= -f2-)
ADM=$(curl -s -X POST "$KC/realms/master/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  -d "username=$U" -d "password=$P" | jq -r .access_token)
```

## 1. Which conditions exist, and which does not

A flow step can be conditional. Ask Keycloak what conditions it has:

```bash
curl -s "$KC/admin/realms/formation/authentication/authenticator-providers" \
  -H "Authorization: Bearer $ADM" \
  | jq -r '.[] | select(.id | startswith("conditional-")) | "\(.id)\t\(.displayName)"'
```

Read that list carefully, and notice what is **not** in it. There is a condition
on a role, on a user attribute, on a credential, on a client scope. There is no
condition on a **group**.

That matters, because teams are groups. The way through is a role: the group
carries the role, and the condition tests the role. Check that a group can
carry one:

```bash
curl -s "$KC/admin/realms/formation/groups" -H "Authorization: Bearer $ADM" \
  | jq -r '.[] | "\(.name)\t\(.id)"'
```

And remember this when you verify your work: a role a group carries does **not**
appear in an account's direct roles. It appears in its effective ones:

```bash
ID=$(curl -s "$KC/admin/realms/formation/users?username=resp-exploitation&exact=true" \
  -H "Authorization: Bearer $ADM" | jq -r '.[0].id')
echo "directs   :"
curl -s "$KC/admin/realms/formation/users/$ID/role-mappings" \
  -H "Authorization: Bearer $ADM" | jq -c '[.realmMappings[]?.name]'
echo "effectifs :"
curl -s "$KC/admin/realms/formation/users/$ID/role-mappings/realm/composite" \
  -H "Authorization: Bearer $ADM" | jq -c '[.[].name]'
```

## 2. What a copy of the browser flow contains

Copy the flow, on a throwaway name, and read what you get:

```bash
curl -s -o /dev/null -w 'copie : HTTP %{http_code}\n' -X POST \
  "$KC/admin/realms/formation/authentication/flows/browser/copy" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d '{"newName":"demo-tuto"}'

curl -s "$KC/admin/realms/formation/authentication/flows/demo-tuto/executions" \
  -H "Authorization: Bearer $ADM" \
  | jq -r '.[] | "niveau=\(.level)\t\(.requirement)\t\(.providerId // "-")\t\(.displayName)"'
```

Read the indentation that `niveau` gives you. There are **two** conditional
sub-flows, and each one has its own `conditional-user-configured`:

- one under *Conditional Organization*, which has nothing to do with second
  factors;
- one under *Conditional 2FA*, which is the one the challenge is about.

This is worth seeing now, because removing the wrong one leaves the trap in
place and breaks something else. The sub-flow has its own address:

```bash
curl -s "$KC/admin/realms/formation/authentication/flows/demo-tuto%20Browser%20-%20Conditional%202FA/executions" \
  -H "Authorization: Bearer $ADM" \
  | jq -r '.[] | "\(.requirement)\t\(.providerId // "-")\t\(.displayName)"'
```

Four lines, and they are the whole subject: a condition, a credential
condition, the code form, and two options that are switched off.

## 3. What "user configured" actually means

`conditional-user-configured` reads, in full: *apply this sub-flow only if the
user has already configured the credential it asks for*.

Read it twice. It means the second factor is demanded from people who have one,
and skipped for people who do not. For an account with no second factor, the
whole sub-flow is skipped, including the step you set to `REQUIRED`.

That is why the console can show a flow with a second factor in it while nobody
is actually asked for one. The setting is right, the effect is nothing, and
there is no message anywhere.

Delete the throwaway copy. Note the address: a flow is deleted by its
**identifier**, not by its name, where its executions are read by **name**. The
inconsistency is Keycloak's, and a delete by name answers 404 without deleting
anything:

```bash
ID_FLUX=$(curl -s "$KC/admin/realms/formation/authentication/flows" \
  -H "Authorization: Bearer $ADM" \
  | jq -r '.[] | select(.alias=="demo-tuto") | .id')
curl -s -o /dev/null -w 'suppression : HTTP %{http_code}\n' -X DELETE \
  "$KC/admin/realms/formation/authentication/flows/$ID_FLUX" \
  -H "Authorization: Bearer $ADM"
curl -s "$KC/admin/realms/formation/authentication/flows" \
  -H "Authorization: Bearer $ADM" | jq -c '[.[] | select(.builtIn == false) | .alias]'
```

An empty list. If it is not empty, something from an earlier attempt is still
there, and your next copy will fail with a conflict on a name already taken.

## What the challenge asks now

You have seen that there is no group condition, that a copy of the browser flow
holds two conditional sub-flows, and that "user configured" means the opposite
of what one hopes.

The challenge asks for a copy, a role condition on the right sub-flow, the
removal of the one that defeats it, a phishing-resistant option, and a password
policy that trusts length rather than composition.

```bash
dsoxlab check iam-07-mfa-keycloak   # grade
dsoxlab hint  iam-07-mfa-keycloak   # one hint, at the cost of points
```
