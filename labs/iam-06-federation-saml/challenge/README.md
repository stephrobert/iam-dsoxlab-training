# Challenge: both sides of a SAML exchange

Two realms on `idp.lab`, both served by the same Keycloak.

| Realm | Role | State |
|---|---|---|
| `formation` | **issuer** of assertions | holds `alice` and the group `devops` |
| `partenaire-sp` | **consumer**, standing in for the partner's tool | empty, with its own `devops` group and an OIDC client |

`/opt/iam-lab/identifiants-lab.txt` holds the entity identifier of the
consumer, its assertion consumer address, the expected alias, the issuer's
metadata URL, and the test account.

The witness application is already running on port `9080`, pointed at the
**consumer**. It asks for the identity provider named `saml-formation`
directly, so you will not see the consumer's own login page.

## What is expected

**On the issuer side**, in `formation`:

1. A **SAML client** whose client id is the consumer's entity identifier, with
   the consumer's assertion consumer address as its redirect.
2. **Signed assertions**, with an algorithm that is not SHA-1.
3. Mappers carrying the **email, the first name, the last name** and the
   **group membership** into the assertion.

**On the consumer side**, in `partenaire-sp`:

4. A **SAML identity provider** with the alias `saml-formation`, enabled, that
   **requires** signed assertions and **validates** the signature against the
   issuer's certificate.
5. Mappers reading those attributes onto the account.
6. A mapper putting the account into the `devops` group when the assertion says
   so.

Then a sign-in, which creates the account.

## What is proven, and how

No test reads an XML assertion. They read what each side declares, then they
**play the whole journey** the way a browser would, and finally they read the
account the consumer ended up with:

- the client exists with the right entity identifier and signs its assertions;
- the consumer requires and validates the signature, against the issuer's
  certificate, for the right issuer;
- the journey ends on the application showing the user's name;
- the account carries the email, the first name and the last name;
- the account is in `devops`.

## Constraints

- The alias is **`saml-formation`**. It decides the consumer's assertion
  consumer address, which the issuer's client must declare, and the witness
  application names it.
- The consumer does not sign its requests. Requiring its signature would refuse
  every connection.
- Read the issuer's certificate from its **metadata**. Anywhere else is a
  different certificate, and the consumer would reject every assertion.

## Three things measured, so you do not lose an afternoon to them

**The email alone is not enough.** Without the first name and the last name,
the consumer stops on « Update Account Information » and the sign-in never
completes. Nothing tells you which of the three is missing.

**Groups do not arrive on their own.** The issuer's membership mapper puts them
in the assertion, and the account still arrives with no group at all. The
consumer needs its own mapper to read the attribute and name the group, and
that group must already exist in its realm: a mapper does not create one.

**`syncMode` decides whether a mapper applies to an account that is already
linked.** On an existing account, a mapper set to `INHERIT` reapplies nothing,
which looks exactly like a mapper that does not work. If you are debugging a
mapper, delete the linked account and sign in again.

```bash
dsoxlab check iam-06-federation-saml   # grade
dsoxlab hint  iam-06-federation-saml   # one hint, at the cost of points
```
