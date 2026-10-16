# How this exam works

This is not a tutorial, and there is no `hints.yaml`. There is nothing here
that tells you how to do the work: that is what the four labs before it were
for.

What this page does is tell you how you are judged, so that no part of your
score comes as a surprise.

## What is measured

The **state of the system**, read through the provider's own API, the witnesses'
own endpoints, and the containers' own status. Ten checks:

| # | What it reads |
|---|---|
| 1 | The provider answers, its management port is healthy, a **named** admin account exists, and no bootstrap account remains |
| 2 | The provider **survives a restart** with its data: the test writes a mark, restarts the container, and reads the mark back |
| 3 | The directory's three accounts are known to the realm, and one of them logs in through it |
| 4 | The directory's group carries **its members**, not just its name |
| 5 | The application's client is public, code flow, PKCE S256, with implicit and direct grant **closed** and no wildcard redirect |
| 6 | A **full login journey** goes from the application to the provider and back, and the application shows the person's name |
| 7 | The API answers **401 without a token** and 200 with a correct one |
| 8 | The API answers **403** on a write attempted with a read token |
| 9 | The API **refuses a token issued for another application** |
| 10 | A machine client reads the API and **cannot write to it** |

How you get there is not measured. Console, API calls, a script, a mixture: it
makes no difference. Two of these checks modify state while they run (the
restart, and the mark it writes) and both put things back as they were.

## What the specification gives you

`/opt/iam-lab/identifiants-lab.txt` names the realm, the admin account to
create and its password, the expected URLs and ports, the directory's DNs and
its admin credential, the accounts and their shared password, every client id,
every scope, and the two witnesses' directories and ports.

Nothing is hidden. An exam that made you guess names would measure guessing.

## What you start from

- Docker, Compose and the tools, installed.
- A **populated directory**, listening on the machine, with three accounts and
  two groups. Building it is lab 01, which is not in this exam's scope.
- A **witness application** that knows nothing about any provider, and a
  **witness API that answers everybody**. Both need to be wired.
- **No identity provider at all.** Installing one is the first thing asked.

## One thing worth knowing before you start

The directory lives in its own Compose project, and the provider you install
will live in another. Docker resolves names inside a network, not between two.
The directory therefore publishes its LDAP port on the machine, and the
specification gives you the machine's address.

Do not reach for `127.0.0.1` from inside the provider's container. From there,
`127.0.0.1` is the container.

```bash
dsoxlab check iam-epreuve-n1    # grade
dsoxlab submit iam-epreuve-n1   # grade and record the verdict
```
