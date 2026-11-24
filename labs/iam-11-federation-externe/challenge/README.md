# Fifteen consultants, and no accounts for them

## The situation

The partner company is sending fifteen consultants for six months. They need
access to three of your applications, and they already have accounts: with
their own employer, who manages their passwords, their two-factor devices and,
most importantly, their departures.

You could create fifteen accounts. Everyone does, the first time. Then someone
leaves the partner company in March, nobody tells you, and their account works
until the day someone thinks to ask.

The other way is to let their employer answer for them. Your realm becomes a
**broker**: when a consultant signs in, it sends them to the partner, the
partner authenticates them, and your realm creates a local account linked to
that answer. The password never comes to you, and the day the consultant leaves
the partner company, the partner's refusal is your refusal.

That part is straightforward, and it is not where the afternoon goes.

The afternoon goes into the question nobody asks out loud: **what does a
stranger get, exactly, on arrival?** An account with no group has no rights and
is useless. An account placed by hand has whatever the person who placed it
remembered. And an account that arrives with an administration role is a door
nobody will ever look at again.

There is one more thing, and it is the sharp edge of this whole lab. Your realm
already holds an account with the same email address as one of the partner's
people. Email addresses collide: people change jobs, companies merge, somebody
mistyped something in 2019. If your first-login flow treats a matching address
as proof of identity, then the stranger from the partner company is now that
person. No alert, no trace, nothing to notice.

Two of the partner's people will sign in during the grading. One must get in.
One must not.

## What a stranger gets on arrival

Two realms on `idp.lab`, served by the same Keycloak.

| Realm | Role | State |
|---|---|---|
| `formation` | **broker**, yours | holds a local account `chloe`, and the witness application's client |
| `entreprise-externe` | the partner | holds `dora` and `bob`, and a client it has declared for you |

`/opt/iam-lab/identifiants-lab.txt` holds the partner's discovery URL, the
client and secret **the partner gave you**, the expected alias, both accounts
and their password.

The witness application is running on port `9080`, pointed at your broker, and
it asks for the identity provider named `oidc-partenaire` directly.

### What is expected

1. An **OIDC identity provider** with the alias `oidc-partenaire`, enabled,
   pointed at the partner, that **validates** the signature of its tokens
   against the partner's published keys.
2. A group named **`partenaires`**, declared as a **default group of the
   realm**. Creating the group is not enough.
3. The first-login flow must **not** link a stranger to an existing local
   account on the strength of a matching email.

Then two sign-ins, which is where the grading happens.

### What is proven, and how

The tests play two journeys, and expect **opposite** results:

| Account | Its email | Expected |
|---|---|---|
| `dora` | matches nobody | the journey **completes**, the account arrives in `partenaires`, with no administration role |
| `bob` | is `chloe`'s email | the journey **stops**, on a screen naming the conflict, and `chloe` is untouched |

The second is the one that matters. A refusal you can see is worth more than a
setting you can read.

### Constraints

- The alias is **`oidc-partenaire`**. The partner has already declared the
  return address it produces: changing it refuses every connection.
- The client and its secret come **from the partner**. Do not create your own:
  the token exchange would be refused.
- Read the partner's endpoints from its **discovery document**. Its keys are to
  be **read from it**, not copied: a partner that rotates its keys must not
  break your broker.

### Three things to know before you start

**A default group is a property of the realm, not of the group.** Creating
`partenaires` puts nobody in it. The realm has to name it as a default.

**A default group applies at account creation.** Declare it after the first
sign-in and the account already created stays outside, which looks exactly like
a default group that does not work. Delete the linked account and sign in
again.

**Keycloak's own first-login flow already protects you.** It creates the
account when the identity is new, and when an address already exists it asks
for confirmation and a verification. The work here is to **not** replace it
with something that links blindly. If you go looking for a setting to turn on,
you are looking for the wrong thing.

```bash
dsoxlab check iam-11-federation-externe   # grade
dsoxlab hint  iam-11-federation-externe   # one hint, at the cost of points
```
