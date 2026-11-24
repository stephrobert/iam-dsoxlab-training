# She left in March

## The situation

Morgane handed in her notice in February and left at the end of March. Her
manager told HR, HR told the directory team, and somebody ticked a box.

In November, during an audit, someone pulls the list of accounts and finds her.
Not deleted, which is correct. Not disabled either, which is not. Still in the
operations group, which gives her access to production. And with a role nobody
remembers granting, attached directly to her account rather than to a group,
which is why no review by groups has ever shown it.

The audit asks one question: was she able to connect between April and
November? Nobody can answer, because nobody looked.

You have the same situation, eight months earlier. Morgane is in the directory,
federated into the provider, in a group, with a role granted directly to her,
and with **an open session right now**.

Four gestures, and the order matters more than you would think. Three of them
fail silently if done wrong: the provider will tell you it worked, the console
will show what you expect, and the access will still be there.

Then write the review file. Not because a process demands it, but because the
only answer to the audit's question is a file dated the day of the departure
that says what she had. Everything else is a memory.

## Four gestures, in the right order

The directory is federated into the realm `formation`, read only, with its
group mapper. Four people are in it, and `morgane` is leaving.

`/opt/iam-lab/identifiants-lab.txt` names who leaves, who stays, the role
granted directly, and where to write the review.
`/opt/iam-lab/jetons-de-la-session.txt` holds the tokens of a session the setup
opened for her: the tests use them, do not change them.

### What is expected

1. `morgane` no longer belongs to any group, and no longer holds the role that
   was granted to her directly.
2. Her account is **disabled**, and **still present**.
3. She has **no active session**.
4. Her refresh token is refused.
5. A review file exists at the path given, listing **every** account with its
   groups **and** its directly granted roles, reflecting the state **after**
   the departure.

And the three people who stay must be untouched.

### Three things that fail silently

**A session survives the disabling.** Measured: after setting the account to
disabled, it still counts one active session. The account page says disabled.
The session continues. You have to close it.

**The provider refuses to remove a federated group membership**, and it is
right to: `Not possible to delete LDAP group mappings as mapper mode is
READ_ONLY`. The directory owns that membership. Remove it at the source.

**The provider caches its view of a federated account.** After removing the
membership at the source and synchronising the mapper, the provider still
returns the old groups, and the synchronisation answers `5 updated groups`.
There is a third thing to do.

### And one thing the order decides

A synchronisation **does not pick up a disabled account**. Disable first, and
the membership you removed at the source stays in the provider for good, with
no error anywhere. The gestures have an order, and it is not the one urgency
suggests.

### The review file

JSON, at the path from `identifiants-lab.txt`. One entry per account, each
naming the account, its groups and its roles. The shape is yours as long as
each entry carries a `username`, a `groupes` or `groups` key, and a `roles` key.

Two things are graded about it: it must be **complete**, and it must describe
the state **after** your work. A review written before the removals describes a
world that no longer exists, which is worse than no review at all.

Roles matter as much as groups. `morgane` holds one granted directly to her
account, and a review by groups alone would never show it. That is why it is in
this lab.

```bash
dsoxlab check iam-08-depart-collaborateur   # grade
dsoxlab hint  iam-08-depart-collaborateur   # one hint, at the cost of points
```
