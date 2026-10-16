# Tutorial: three mechanisms to see at work

This tutorial does not do the challenge. It shows you the three mechanisms the
challenge needs, at work, on a throwaway account that is not one of the three
you have to create.

Read the directory's details first:

```bash
cat /opt/iam-lab/identifiants-lab.txt
BASE=$(grep '^BASE_DN=' /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)
ADMIN=$(grep '^ADMIN_DN=' /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)
MDP=$(grep '^ADMIN_MOT_DE_PASSE=' /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)
echo "base : $BASE"
```

Note `cut -d= -f2-`, with the dash. The base DN is `dc=formation,dc=lab`: it
contains the separator, and `-f2` alone would hand you `dc`. Every query would
then fail with `Naming violation (64): Missing DN value`, which points at the
query and not at the variable that built it.

## 1. What is already in the tree

Ask the directory what it holds, before writing anything:

```bash
ldapsearch -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" \
  -b "$BASE" -LLL '(objectClass=*)' dn
```

Three groups and one account, all belonging to the directory itself. And notice
what is **not** listed: `ou=people` and `ou=groups` are not entries you can see
or create. LLDAP imposes that layout. You will not be organising the tree, you
will be filling it.

Look at the administrator in full, and at the object classes LLDAP gives an
account:

```bash
ldapsearch -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" \
  -b "$BASE" -LLL '(uid=admin)'
```

`inetOrgPerson`, `posixAccount`, `mailAccount`, `person`. You declare one of
them when you create an account; the directory adds the others.

## 2. Writing, and reading back immediately

Create a throwaway account, then read it back at once. Reading back after each
write is the habit this lab exists to build:

```bash
cat > /tmp/demo.ldif <<LDIF
dn: uid=demo-tuto,ou=people,$BASE
objectClass: inetOrgPerson
uid: demo-tuto
cn: Démo Tutoriel
sn: Tutoriel
mail: demo-tuto@formation.lab
LDIF

ldapadd -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" -f /tmp/demo.ldif
ldapsearch -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" \
  -b "$BASE" -LLL '(uid=demo-tuto)'
```

Two things in that output.

The `cn` came back as `cn:: RMOpbW8gVHV0b3JpZWw=`, with a **double colon**.
That is LDIF saying "this value is base64", because it is not plain ASCII.
Decode it to be sure:

```bash
echo 'RMOpbW8gVHV0b3JpZWw=' | base64 -d; echo
```

It is correct. One of the accounts you have to create carries an accent, and
its `cn` will come back the same way. Decoding before concluding saves an hour.

And LLDAP added an attribute of its own, `last_name`, alongside the `sn` you
declared. A lightweight directory keeps its own model and maps yours onto it.

## 3. Membership, and the write that lies

Create a throwaway group and try to put the account in it with LDIF alone,
exactly as an LDAP server would normally allow:

```bash
cat > /tmp/demo-grp.ldif <<LDIF
dn: cn=demo-grp,ou=groups,$BASE
objectClass: groupOfNames
cn: demo-grp
member: uid=demo-tuto,ou=people,$BASE
LDIF

ldapadd -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" -f /tmp/demo-grp.ldif
echo "--- et le membre, relu ---"
ldapsearch -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" \
  -b "ou=groups,$BASE" -LLL '(cn=demo-grp)' member
```

**The add succeeded, and the group has no member.** No warning, no error: the
`member:` line was accepted and dropped. This is the refusal that looks like a
success, and reading back is the only way to see it.

Try the other obvious route, modifying the group:

```bash
cat > /tmp/demo-mod.ldif <<LDIF
dn: cn=demo-grp,ou=groups,$BASE
changetype: modify
add: member
member: uid=demo-tuto,ou=people,$BASE
LDIF
ldapmodify -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" -f /tmp/demo-mod.ldif
```

`Invalid DN syntax (34)`, and the message says `Invalid username: Unexpected DN
format. Got "cn=demo-grp,…", expected "uid=id,ou=people,…"`. LLDAP read the
group's DN as if it were a person's. The message is misleading, and the
conclusion is clear: memberships do not go through LDAP here.

They go through the directory's own API. Get a token, list the groups to find
the numeric id the API uses, and add the member:

```bash
WEB=http://127.0.0.1:17170
JETON=$(curl -s -X POST "$WEB/auth/simple/login" \
  -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg m "$MDP" '{username:"admin", password:$m}')" | jq -r .token)

GID=$(curl -s -X POST "$WEB/api/graphql" \
  -H "Authorization: Bearer $JETON" -H 'Content-Type: application/json' \
  -d '{"query":"{ groups { id displayName } }"}' \
  | jq -r '.data.groups[] | select(.displayName == "demo-grp") | .id')
echo "id du groupe : $GID"

curl -s -X POST "$WEB/api/graphql" \
  -H "Authorization: Bearer $JETON" -H 'Content-Type: application/json' \
  -d "$(jq -nc --argjson g "$GID" '{query:"mutation($u: String!, $g: Int!) { addUserToGroup(userId: $u, groupId: $g) { ok } }", variables:{u:"demo-tuto", g:$g}}')"
echo
```

Now read it back, from both sides:

```bash
ldapsearch -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" \
  -b "ou=groups,$BASE" -LLL '(cn=demo-grp)' member uniqueMember
ldapsearch -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" \
  -b "ou=people,$BASE" -LLL '(uid=demo-tuto)' memberOf
```

`member`, `uniquemember` and `memberOf` are all served now. The API wrote it,
and LDAP reads it: that is the split you are working with.

One last thing worth knowing. The API answers HTTP `200` **with** an `errors`
array when a call fails. Watching the status code alone would make a failed
call look like a success:

```bash
curl -s -X POST "$WEB/api/graphql" \
  -H "Authorization: Bearer $JETON" -H 'Content-Type: application/json' \
  -d '{"query":"mutation { addUserToGroup(userId: \"personne-inexistante\", groupId: 1) { ok } }"}' \
  -o /tmp/reponse -w 'code HTTP : %{http_code}\n'
cat /tmp/reponse; echo
```

Clean up the throwaway objects:

```bash
curl -s -o /dev/null -X POST "$WEB/api/graphql" \
  -H "Authorization: Bearer $JETON" -H 'Content-Type: application/json' \
  -d "$(jq -nc --argjson g "$GID" '{query:"mutation($g: Int!) { deleteGroup(groupId: $g) { ok } }", variables:{g:$g}}')"
ldapdelete -x -H ldap://127.0.0.1:3890 -D "$ADMIN" -w "$MDP" \
  "uid=demo-tuto,ou=people,$BASE"
rm -f /tmp/demo.ldif /tmp/demo-grp.ldif /tmp/demo-mod.ldif /tmp/reponse
echo "nettoye"
```

## What the challenge asks now

You have seen that the tree is imposed, that LDIF hands back base64 for
anything but plain ASCII, and that memberships go through the API while
everything else goes through LDAP.

The challenge asks for three people, two groups, exact memberships, and proof
that all of it survives a restart.

```bash
dsoxlab check iam-01-annuaire-lldap   # grade
dsoxlab hint  iam-01-annuaire-lldap   # one hint, at the cost of points
```
