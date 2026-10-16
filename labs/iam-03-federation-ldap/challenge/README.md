# Challenge: one source of truth, read only

The directory and the provider both run on `idp.lab`, in containers.
`/opt/iam-lab/identifiants-lab.txt` holds the base DN, the two branches, the
bind account, and the password of the three directory accounts.

The directory already holds what the first lab asks you to create: `aline`,
`bruno` and `chloé`, in the groups `devops` and `lecteurs`. The provider knows
nobody.

## What is expected

1. A **user federation** of type LDAP in the `formation` realm, enabled, with
   **import on** and in **read only** mode.
2. It points at the directory's user branch, and reads `uid` as the username.
3. A **group mapper** on that federation, pointing at the group branch and
   reading membership from the attribute the directory publishes.
4. Both **synchronisations** have been run: accounts, then groups. Declaring
   does not import.
5. `aline` can obtain a token on the realm with the password from
   `identifiants-lab.txt`.

## What is proven, and how

The tests do not read your configuration to judge it good. They look at what
the provider **knows** and what it **refuses**:

- the three people are known to the realm, each linked to the federation, each
  with their email;
- `devops` holds exactly `aline` and `bruno`, `lecteurs` exactly `bruno` and
  `chloe`;
- `aline` gets a token;
- a request to change a federated account's first name is **refused**, with
  `error-user-attribute-read-only`.

The last one is the one that cannot be faked. A mode set with no effect looks
exactly like a mode set correctly, until someone edits a name.

## Constraints

- The realm is `formation`. One federation, not two: with two, priority
  decides who answers and the result stops being predictable.
- The directory publishes membership in `member` on the group side, and also in
  `uniqueMember` and `memberOf`.
- The accounts carry `inetOrgPerson`, and their identifier is `uid`.
- Do not change anything in the directory: it is the source now.

## The trap, stated plainly, because it costs an afternoon

Keycloak runs in a container. Inside that container, `127.0.0.1` is the
container itself, not the machine. Measured from it: `127.0.0.1:3890` is
**closed**, `lldap:3890` is **open**.

With the wrong address, everything looks right. The federation is created, it
is enabled, and the synchronisation answers HTTP `200` with
`0 imported users, 0 updated users`. No error, no warning. Read the number the
synchronisation gives back, every time.

For `entryUUID`: the directory gives each entry a stable identifier that
survives a rename, where its DN does not. Telling the federation to use it is
what keeps a renamed account linked to its sessions instead of arriving as a
new person.

```bash
dsoxlab check iam-03-federation-ldap   # grade
dsoxlab hint  iam-03-federation-ldap   # one hint, at the cost of points
```
