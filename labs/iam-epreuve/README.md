# How this exam works

This is not a tutorial, and there is no `hints.yaml`. Nothing here tells you
how to do the work: the labs did that.

What this page tells you is how you are judged.

## The sixteen checks

All of them read the **state of the system**: the provider's own API, the
witnesses' endpoints, the containers' status, the database itself.

| # | What it reads |
|---|---|
| 1 | The provider answers, management port healthy, **named** admin, no bootstrap account left |
| 2 | The provider **survives a restart** with its data |
| 3 | The directory's accounts are known to the realm, and one logs in through it |
| 4 | The directory's group carries **its members** |
| 5 | The application's client: public, code flow, PKCE S256, implicit and direct grant closed, no wildcard |
| 6 | A **full login journey** works and shows the person's name |
| 7 | The API answers **401** without a token, 200 with a correct one |
| 8 | The API answers **403** on a write with a read token |
| 9 | The API **refuses a token issued for another application** |
| 10 | A machine client reads the API and **cannot write** |
| 11 | The second factor is imposed **through the group**, with a configured role condition, and `conditional-user-configured` gone |
| 12 | Two journeys end **differently**: the concerned account is stopped, the spared one gets in |
| 13 | The password policy relies on **length**, with no composition rules and no expiry |
| 14 | The departure is finished: **disabled, no group, no session** |
| 15 | The access review is **complete and current**, with roles as well as groups |
| 16 | A database backup **restores into an empty database** with the accounts in it |

Several of these checks modify state while they run: the restart in 2, the
journeys in 12, the throwaway database in 16. All of them put things back.

## Read the specification carefully

`/opt/iam-lab/identifiants-lab.txt` names everything, and it names something
you need before you start: **which of the three accounts plays which role**.

- `UTILISATEUR` plays the login journey and uses the API. It is **not** in the
  sensitive group, and that is deliberate: the second factor you are about to
  impose would otherwise stop its journey, and check 6 would fail on the very
  exigence check 11 asks you to put in place.
- `COMPTE_CONCERNE` is in the sensitive group, and must be stopped by the second
  factor.
- `COMPTE_EPARGNE` must get in without one.
- `QUI_PART` is the departure.

## What you start from

Docker and the tools. A populated directory on the machine, in its own Compose
project. A witness application that knows nothing, and a witness API that
answers everybody. **No identity provider.** No backup. No review.

## Two things that cost an afternoon each

The directory and the provider live in **different Compose projects**, so no
name resolves between them. The directory publishes its LDAP port on the
machine, and from inside the provider's container `127.0.0.1` is the container.

A federated membership **cannot be removed from the provider** when the mapper
is read-only. It is removed at the source, resynchronised, and then the
provider's cache of federated accounts has to be cleared, which is a separate
call that nothing points you to.

```bash
dsoxlab check iam-epreuve    # grade
dsoxlab submit iam-epreuve   # grade and record the verdict
```
