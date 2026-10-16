# Challenge: an identity provider you leave in production

You work in `/opt/keycloak-lab`, on the `idp.lab` machine. The
`identifiants.txt` file there holds the administration account you must
create, and `LISEZ-MOI.txt` says where to write.

## What is expected

Keycloak must run, backed by PostgreSQL, and deliver four things:

1. its **health endpoint** must answer and report itself ready;
2. the database actually in service must be **PostgreSQL**, not the one
   Keycloak embeds for development;
3. a realm named **`formation`** must exist and serve its OIDC discovery;
4. the named account from `identifiants.txt` must **administer the server**,
   and the `temp-admin` bootstrap account must no longer work, whether deleted
   or disabled.

## What is proven, and how

The tests do not open your Compose file: they question the server. You reach
the result by whatever path you choose, as long as the server delivers what is
asked.

The last test **restarts your containers** and checks the realm is still
there. That is the only way to tell a database that persists from one that
keeps up appearances until the first shutdown.

## Constraints

- The Compose file is named `compose.yaml` and lives in `/opt/keycloak-lab`.
  The rest is yours: service, volume and network names.
- The two ports the tests question are the ones Keycloak exposes by default for
  its application and for its management. Publishing them is up to you.
- Do not change the values in `identifiants.txt`: the tests authenticate with
  them.

## Two traps that cost others hours

A server that answers is not a server that persists. The startup command
decides which database is used, and it can contradict what you declared in the
environment.

A Keycloak **server** administrator does not live in the application realm. An
account created in the right place with the right roles administers what it
should; created elsewhere, it only administers its own realm.

```bash
dsoxlab check iam-02-keycloak-installer   # grade
dsoxlab hint  iam-02-keycloak-installer   # one hint, at the cost of points
```
