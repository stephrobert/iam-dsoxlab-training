# Monday morning, and nothing is wired

## The situation

The company has a directory. It has been there for years, it holds the three
people who will use what you build today, and it works. It is the only thing
that works.

There is no identity provider. There is an application that shows notes, and an
API that serves them, and both were written by somebody who left. The
application has no login page. The API answers anybody who asks, which is how
the notes ended up in a support ticket last month, pasted by somebody who was
not supposed to see them.

You have the machine, the directory, and until the end of the morning.

What is expected is not a demonstration. It is a provider that is still there
after the machine reboots, a directory whose accounts and groups are usable
through it, an application that sends people to the provider and shows their
name when they come back, and an API that refuses what it should refuse.

That last one is the part people get wrong, and they get it wrong in a specific
way: they make the API check that the token is valid. A token from this
provider, for this person, issued for an entirely different application, is
valid. If that is enough for your API, then every application in the realm can
read the notes, and you have built the ticket from last month again with more
steps.

There are no hints in this exercise. The tests read the state of the system, so
how you get there is your business: console, API, script, it makes no
difference. What matters is what is true at the end.

The specification is in `/opt/iam-lab/identifiants-lab.txt`. It names
everything the tests look for, because an exam that hid the names would measure
guesswork.

## Level 1 exam: four tasks, ninety minutes, no hints

Read `/opt/iam-lab/identifiants-lab.txt` first. It is the specification, and
every name the tests look for is in it.

### 1. Install an identity provider that lasts

It must answer on the URL the specification gives, expose a health endpoint on
the management port, and **keep its data across a restart**. It must have a
**named** administrator, and no bootstrap account left behind: a shared account
that administers a server leaves no trace of who did what.

The realm named in the specification must exist.

### 2. Federate the directory

Its three accounts must be usable through the provider, and one of them must be
able to log in. Its groups must arrive **with their members**: a group with the
right name and nobody in it is the usual outcome, and it passes a visual
inspection.

Read-only federation. The provider does not write into the directory.

### 3. Wire the witness application

OIDC, authorization code flow, PKCE S256. The implicit flow closed, the direct
grant closed, redirect URIs exact.

Then configure the witness application itself and start it, so that a full
journey works: the application sends the person to the provider, the provider
sends them back, and the application shows their name.

### 4. Close the witness API

Right now it answers everybody. It must check, on every request:

- the **signature**, so the token comes from the provider;
- the **issuer**, so it comes from the right realm of that provider;
- the **audience**, so it was issued for this API;
- the **expiry**.

Then the **scope**, which is a different question: the token is valid, and it
may still not be enough. A read token used for a write gets **403**, not 401.
A missing or invalid token gets **401**.

A machine client must be able to read the API, and must not be able to write to
it. In client credentials nobody is there to ask for a scope, so whatever it
needs has to be attached by default, and whatever it does not need must not be.

### How you are judged

Ten checks on the state of the system, listed in this lab's `README`. The pass
mark is 70 percent of the scale, and `dsoxlab submit` gives you the verdict.

```bash
dsoxlab check iam-epreuve-n1
dsoxlab submit iam-epreuve-n1
```
