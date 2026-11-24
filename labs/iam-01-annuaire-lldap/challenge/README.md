# Before any provider, there is a directory

## The situation

The identity provider is installed and it works. It has exactly one account in
it: the administrator who installed it. Nobody else exists, so nobody else can
sign in.

That is the normal state of things, and it is where every identity project
begins. A provider does not invent people. It reads them somewhere, and that
somewhere is a directory.

You have LLDAP running on `idp.lab`, with its tree and its administrator. Three
people are joining: Aline in the operations team, Bruno who straddles
operations and auditing, Chloé who only ever reads. Two groups will carry those
roles, and the next lab will teach the provider to read them.

The job sounds like five minutes of LDIF, and it is not, because LLDAP is a
**lightweight** directory. It speaks LDAP, it accepts some writes, and it
refuses others in ways that are not obvious. One of those refusals looks
exactly like a success.

Find out which, and get the memberships in place anyway. Then restart the
container and look again: a directory that forgets is not a directory, and the
only way to know is to try.

## Three people, two groups, and one refusal to find

The directory runs on `idp.lab`. `/opt/iam-lab/identifiants-lab.txt` holds its
base DN, its administrator DN and password, and both of its URLs.

LLDAP imposes its own tree: `ou=people` and `ou=groups` already exist, and it
will not accept an organisational unit you create elsewhere. Work inside them.

### What is expected

Three accounts under `ou=people`:

| uid | cn | mail |
|---|---|---|
| `aline` | `Aline Dupont` | `aline@formation.lab` |
| `bruno` | `Bruno Keller` | `bruno@formation.lab` |
| `chloe` | `Chloé Nguyen` | `chloe@formation.lab` |

Two groups under `ou=groups`, with exactly these members:

| cn | members |
|---|---|
| `devops` | `aline`, `bruno` |
| `lecteurs` | `bruno`, `chloe` |

Exactly those. A group with one person too many grants a right nobody asked
for, and that is what an access review digs up months later.

### What is proven, and how

Every test runs `ldapsearch`, because that is what an identity provider will
do next:

- each account exists with its `cn` and its `mail`;
- each group holds exactly its members, read from the group;
- each account's `memberOf` names its groups, read from the account;
- a filter `(memberOf=cn=devops,…)` returns the right people;
- the data survives `docker restart` of the directory container.

The last one is not a formality. A declared volume does not prove it is mounted
where the data is written, and the only way to know is to stop the thing.

### Constraints

- The names are fixed: the tests look them up.
- Do not touch the `admin` account or the `lldap_*` groups: they are the
  directory's own.
- Nothing is required about *how* you write. LDIF, the API, the web interface:
  the tests read the result.

### The refusal that looks like a success

LLDAP is a lightweight directory, and it does not accept every write an LDAP
server usually does. One of its refusals is silent: the command returns
success, and nothing happens.

Find it by checking your work after each step instead of at the end. Read back
what you wrote, with `ldapsearch`, before moving on. The directory has an API
as well, and its schema lists what it can do.

Non ASCII values come back base64 encoded, signalled by a double colon
(`cn:: Q2hs…`). That is the LDIF format, not a mistake: decode it before
concluding your account is wrong.

```bash
dsoxlab check iam-01-annuaire-lldap   # grade
dsoxlab hint  iam-01-annuaire-lldap   # one hint, at the cost of points
```
