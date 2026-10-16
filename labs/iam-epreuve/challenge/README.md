# Final exam: eight tasks, two hours, no hints

Read `/opt/iam-lab/identifiants-lab.txt` first. It is the specification, and it
tells you which account plays which role in this exam.

## 1. A provider that lasts

Answering on the URL given, health on the management port, data surviving a
restart, a **named** administrator, no bootstrap account left behind. The realm
named in the specification must exist.

## 2. The directory, federated

Its accounts usable through the provider, one of them logging in. Its groups
arriving **with their members**. Read-only: the provider does not write into
the directory.

## 3. The application, wired

OIDC, code flow, PKCE S256, implicit and direct grant closed, exact redirect
URIs. Then configure and start the witness so a full journey works and shows
the person's name.

## 4. The API, closed

Signature, issuer, audience, expiry. Then scope: **403** when the token is
valid but insufficient, **401** when it is absent or invalid. A machine client
reads and does not write.

## 5. A second factor, for the sensitive group only

Imposed **through the group**, so that it follows membership rather than a list
of names. The account named `COMPTE_CONCERNE` must be stopped by it; the one
named `COMPTE_EPARGNE` must get in.

Mind the condition that only requires a factor from those who already have one:
with it in place, the step can be required and nobody is actually required to
do anything.

Keep the shipped browser flow intact. Work on a copy, and activate the copy.

## 6. A password policy that holds up

Length first. No composition rules, no forced expiry: both produce predictable
passwords written on paper.

## 7. The departure, finished

`QUI_PART` must end up **disabled**, with **no group** and **no session**.

Two of those three gestures report success without doing anything, and one of
them is refused by the provider itself. Check the state after each one rather
than the status code.

## 8. A review, and a backup

The review lists every account with its groups **and its roles**, and it
describes the state **after** the departure, not before.

The backup is of the **database**, and the exam restores it into a database it
creates for the purpose. An export of the realm will not pass: it carries no
events, so no record of who logged in.

## How you are judged

Sixteen checks on the state of the system, listed in this lab's `README`. The
pass mark is 75 percent of the scale.

```bash
dsoxlab check iam-epreuve
dsoxlab submit iam-epreuve
```
