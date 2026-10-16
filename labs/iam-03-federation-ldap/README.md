# Tutorial: three mechanisms to see at work

This tutorial does not do the challenge. It shows you the three mechanisms the
challenge needs, at work, and it starts with the one that wastes the most time.

## 1. A container's localhost is its own

Both services run in containers. Look at what the provider's container can
actually reach:

```bash
for nom in lldap socle-iam-lldap-1 127.0.0.1; do
  echo -n "$nom resout : "
  docker exec socle-iam-keycloak-1 getent hosts "$nom" 2>/dev/null \
    | head -1 || echo "(rien)"
done
```

Three names resolve, and that is not the question. The question is which one
answers on the directory's port:

```bash
for nom in lldap 127.0.0.1; do
  if docker exec socle-iam-keycloak-1 \
       sh -c "timeout 3 bash -c 'echo > /dev/tcp/$nom/3890'" 2>/dev/null; then
    echo "$nom:3890 ouvert"
  else
    echo "$nom:3890 ferme"
  fi
done
```

`127.0.0.1:3890` is closed. Not filtered, not slow: there is nothing there,
because inside that container `127.0.0.1` is the container.

And yet from the machine itself, the same address works perfectly:

```bash
BASE=$(grep '^BASE_DN=' /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)
ADMIN=$(grep '^ADMIN_DN=' /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)
MDP=$(grep '^ADMIN_MOT_DE_PASSE=' /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)
ldapwhoami -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP"
```

That is the whole trap. You test the address from your shell, it works, you
paste it into the provider's configuration, and the provider cannot reach it.
The address you give a service must be reachable **from that service**.

## 2. What the directory actually publishes

Before configuring anything, look at what the federation will have to read.
This is the information every field of the configuration asks for:

```bash
echo "--- un compte ---"
ldapsearch -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" \
  -b "ou=people,$BASE" -LLL '(uid=aline)'
echo "--- un groupe ---"
ldapsearch -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" \
  -b "ou=groups,$BASE" -LLL '(cn=devops)'
```

Read it as a list of answers.

The identifier is `uid`, not `cn` and not `mail`: that is the username
attribute. The object class is `inetOrgPerson`. The branch is `ou=people`.
On the group side, the members are listed in `member`, **as full DNs**, not as
bare identifiers: the configuration has a separate field for that distinction.

And notice `entryuuid`. It is an identifier the directory assigns and never
changes, even if the entry is renamed. A DN changes when someone's identifier
changes; this does not. Telling the federation to key on it is what keeps a
renamed account linked to its sessions instead of arriving as a new person.

## 3. Declaring imports nothing

A federation is a component of the realm. Create a throwaway one, on purpose
with the wrong address, and watch what the synchronisation says:

```bash
KC=http://127.0.0.1:8080
U=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME=' /opt/socle-iam/.env | cut -d= -f2-)
P=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD=' /opt/socle-iam/.env | cut -d= -f2-)
ADM=$(curl -s -X POST "$KC/realms/master/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  -d "username=$U" -d "password=$P" | jq -r .access_token)

ID_REALM=$(curl -s "$KC/admin/realms/formation" \
  -H "Authorization: Bearer $ADM" | jq -r .id)

curl -s -o /dev/null -w 'creation : HTTP %{http_code}\n' -X POST \
  "$KC/admin/realms/formation/components" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg base "$BASE" --arg dn "$ADMIN" --arg mdp "$MDP" \
        --arg parent "$ID_REALM" '{
    name:"demo-mauvaise-adresse", providerId:"ldap",
    providerType:"org.keycloak.storage.UserStorageProvider", parentId:$parent,
    config:{enabled:["true"], importEnabled:["true"], editMode:["READ_ONLY"],
            vendor:["other"], usernameLDAPAttribute:["uid"],
            rdnLDAPAttribute:["uid"], uuidLDAPAttribute:["entryUUID"],
            userObjectClasses:["inetOrgPerson"],
            connectionUrl:["ldap://127.0.0.1:3890"],
            usersDn:[("ou=people," + $base)], authType:["simple"],
            bindDn:[$dn], bindCredential:[$mdp], searchScope:["1"]}}')"

ID_DEMO=$(curl -s \
  "$KC/admin/realms/formation/components?parent=$ID_REALM&type=org.keycloak.storage.UserStorageProvider" \
  -H "Authorization: Bearer $ADM" \
  | jq -r '.[] | select(.name=="demo-mauvaise-adresse") | .id')

echo "--- la synchronisation ---"
curl -s -X POST \
  "$KC/admin/realms/formation/user-storage/$ID_DEMO/sync?action=triggerFullSync" \
  -H "Authorization: Bearer $ADM" | jq -c .
```

`0 imported users`, and the HTTP status was a success. This is the only signal
you get. There is no error, no log line screaming at you, nothing in the
console that turns red.

Now try to change only the address. Read the component back, edit the one
field, and send it:

```bash
LU=$(curl -s "$KC/admin/realms/formation/components/$ID_DEMO" \
     -H "Authorization: Bearer $ADM")
echo "$LU" | jq -c '{connectionUrl: .config.connectionUrl,
                     bindCredential: .config.bindCredential}'

curl -s -o /dev/null -w 'PUT : HTTP %{http_code}\n' -X PUT \
  "$KC/admin/realms/formation/components/$ID_DEMO" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d "$(echo "$LU" | jq '.config.connectionUrl = ["ldap://lldap:3890"]')"
```

`HTTP 400`, and look at what you printed just before: `bindCredential` came
back as `**********`. Keycloak does not hand out secrets it stores, and it
refuses to be given that mask back as a value. The refusal is explicit here,
which is a kindness: a server that accepted it would have broken the binding
and you would be back to `0 imported users` with no idea why.

Put the real secret back, and send it again:

```bash
curl -s -o /dev/null -w 'PUT : HTTP %{http_code}\n' -X PUT \
  "$KC/admin/realms/formation/components/$ID_DEMO" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' \
  -d "$(echo "$LU" | jq --arg mdp "$MDP" \
        '.config.connectionUrl = ["ldap://lldap:3890"]
         | .config.bindCredential = [$mdp]')"

curl -s -X POST \
  "$KC/admin/realms/formation/user-storage/$ID_DEMO/sync?action=triggerFullSync" \
  -H "Authorization: Bearer $ADM" | jq -c .
```

Now it imports. One field, and the difference between a federation that works
and a federation that silently sees nobody. Measured: four accounts, because
the directory's own administrator is one of them.

Look at what arrived, and at what did not:

```bash
curl -s 'http://127.0.0.1:8080/admin/realms/formation/users?briefRepresentation=true' \
  -H "Authorization: Bearer $ADM" | jq -c '[.[] | {username, email}]'
echo "--- et les groupes ? ---"
curl -s http://127.0.0.1:8080/admin/realms/formation/groups \
  -H "Authorization: Bearer $ADM" | jq -c '[.[].name]'
```

The accounts are there. The groups are **not**, and no amount of re-running
that synchronisation will bring them. Groups come from a second component, with
its own synchronisation, in an explicit direction. That is the third mechanism,
and the challenge needs it.

Clean up the throwaway federation. Removing it also removes the accounts it
imported, because they exist in Keycloak only through it:

```bash
curl -s -o /dev/null -X DELETE \
  "$KC/admin/realms/formation/components/$ID_DEMO" \
  -H "Authorization: Bearer $ADM"
curl -s 'http://127.0.0.1:8080/admin/realms/formation/users?briefRepresentation=true' \
  -H "Authorization: Bearer $ADM" | jq -c '[.[].username]'
```

An empty list. That is worth remembering: a federated account is not a copy you
have to clean up, it is a view that disappears with its source.

## What the challenge asks now

You have seen that an address must be reachable from the service that uses it,
that the directory answers every configuration question if you read an entry,
and that declaring a federation imports nothing until you ask it to.

The challenge asks for the federation, read only, the group mapper, both
synchronisations, and a sign-in with an account the provider never created.

```bash
dsoxlab check iam-03-federation-ldap   # grade
dsoxlab hint  iam-03-federation-ldap   # one hint, at the cost of points
```
