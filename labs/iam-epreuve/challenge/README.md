# Everything, on one machine, before the end of the day

## The situation

The audit is in three weeks. The auditor sent their list of questions early,
which is a courtesy, and the list is short enough to read in a minute and long
enough to explain why nobody has slept well since.

Who can log in. Where their accounts live. What happens when somebody leaves.
Whether anybody has a second factor. Whether you can prove any of it.

Right now the honest answers are: nobody knows, in four places, nothing,
no, and no.

You have a machine, a directory with three people in it, an application that
has no login page, and an API that answers anybody who asks. You have until the
end of the day.

What the auditor will actually check is not your configuration. It is whether
the state of the system matches what you told them. So that is what this exam
checks too: sixteen readings of the system, and not one of them cares how you
got there.

Four of those readings are worth thinking about before you start.

**The provider has to survive a restart.** Not because restarts are frequent,
but because a provider that loses its realm on reboot has no realm, it has a
demonstration.

**The second factor goes to the sensitive group, and only to it.** Imposed on
everybody, it locks out the administrator, and the usual remedy at that point
is to disable the whole thing on Monday morning. Imposed on nobody, which is
the more common outcome, it passes every visual inspection: the step is there,
it is required, and the people who have no second factor walk straight through.

**The departure has to be finished.** Three gestures, and two of them answer
« done » without having done anything. One of them is refused by the provider
itself, politely, in a way you have to go looking for.

**The backup has to restore.** Not exist: restore. This exam creates a
database, puts your backup into it, and counts what came back. An export of the
realm will not pass, and it will not pass for a reason the auditor cares about:
it contains no record of who logged in.

The specification is in `/opt/iam-lab/identifiants-lab.txt`. It names the three
accounts and the role each one plays in this exam, and it is worth reading that
part carefully: one of the three must not be in the sensitive group, and the
specification tells you which.

There are no hints.

## Final exam: eight tasks, two hours, no hints

Read `/opt/iam-lab/identifiants-lab.txt` first. It is the specification, and it
tells you which account plays which role in this exam.

### 1. A provider that lasts

Answering on the URL given, health on the management port, data surviving a
restart, a **named** administrator, no bootstrap account left behind. The realm
named in the specification must exist.

### 2. The directory, federated

Its accounts usable through the provider, one of them logging in. Its groups
arriving **with their members**. Read-only: the provider does not write into
the directory.

### 3. The application, wired

OIDC, code flow, PKCE S256, implicit and direct grant closed, exact redirect
URIs. Then configure and start the witness so a full journey works and shows
the person's name.

### 4. The API, closed

Signature, issuer, audience, expiry. Then scope: **403** when the token is
valid but insufficient, **401** when it is absent or invalid. A machine client
reads and does not write.

### 5. A second factor, for the sensitive group only

Imposed **through the group**, so that it follows membership rather than a list
of names. The account named `COMPTE_CONCERNE` must be stopped by it; the one
named `COMPTE_EPARGNE` must get in.

Mind the condition that only requires a factor from those who already have one:
with it in place, the step can be required and nobody is actually required to
do anything.

Keep the shipped browser flow intact. Work on a copy, and activate the copy.

### 6. A password policy that holds up

Length first. No composition rules, no forced expiry: both produce predictable
passwords written on paper.

### 7. The departure, finished

`QUI_PART` must end up **disabled**, with **no group** and **no session**.

Two of those three gestures report success without doing anything, and one of
them is refused by the provider itself. Check the state after each one rather
than the status code.

### 8. A review, and a backup

The review lists every account with its groups **and its roles**, and it
describes the state **after** the departure, not before.

The backup is of the **database**, and the exam restores it into a database it
creates for the purpose. An export of the realm will not pass: it carries no
events, so no record of who logged in.

### How you are judged

Sixteen checks on the state of the system, listed in this lab's `README`. The
pass mark is 75 percent of the scale.

```bash
dsoxlab check iam-epreuve
dsoxlab submit iam-epreuve
```
