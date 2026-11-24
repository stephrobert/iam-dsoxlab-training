# The application that must stop holding passwords

## The situation

The `notes` application asks its users for a login and a password, checks them
against its own table, and keeps a session. It works. It has worked for six
years.

Then the company bought a second tool, and a third. Each one asks for a password.
Each one keeps its own table. When someone leaves, three tables have to be
updated, and the day someone forgets one, a former employee still reads the
notes.

You have an identity provider running: Keycloak, with its database, on
`idp.lab`. The decision is made, and it is not up for discussion: `notes`
stops asking for passwords. It sends the user to the provider, and the provider
sends them back with proof of who they are.

That proof is a token, and a token is only worth the checks made on it. The
witness application already knows how to make them, all of them. What it does
not know is **who it should talk to**, and the provider does not yet know that
this application exists.

This is the whole job: declare the application to the provider, declare the
provider to the application, and leave nothing open that should be closed.

What you will be graded on is not your configuration file. It is what the
provider **refuses**: a code exchanged without proof of origin, a return address
that was never declared, a password grant that would let the application see the
password again. An integration that works and refuses nothing is an integration
that has not been done.

## An integration that refuses what it should

The provider is running on `idp.lab`, on port `8080`, with a realm named
`formation` and an account in it. `/opt/iam-lab/identifiants-lab.txt` holds
that account.

The witness application lives in `/opt/iam-lab/appli-temoin`. It is complete:
it already starts an authorization code flow with PKCE, and validates the ID
token it gets back down to its nonce. Reading its code will not give you the
answer, because the answer lives in the provider.

### What is expected

1. The application has an identity with the provider: a client named
   **`appli-notes`**, in the `formation` realm.
2. That client is **public** and holds no secret.
3. Only the **authorization code flow** is open. The three other grants are
   closed, and one of them is open by default.
4. **PKCE in S256** is required, not merely offered.
5. The **redirect URIs are exact**. No wildcard, anywhere.
6. The application knows the provider: `configuration.json`, next to
   `appli.py`, declares the `issuer`, the `client_id` and the `redirect_uri`.
7. The application is **running**, and a user from the realm can sign in
   through it.

### What is proven, and how

The tests do not open your configuration. They question the provider's
administration API, and then they **play the flow**, the way a browser would:

- a code exchanged **without** `code_verifier` must be refused;
- a redirect URI that was never declared must be refused;
- the ID token must carry the issuer of this realm, the audience of this
  client, and the nonce that was sent;
- the application's page must end up showing the signed-in user's name.

An attribute set with no effect is the trap this grading exists to catch. It is
not enough for the client's record to say PKCE: the server has to refuse without
it.

### Constraints

- The client is named `appli-notes`. The tests look it up by that name.
- The application listens on port **9080**, and its return path is
  **`/callback`**. The host and the port of the redirect URI are yours; the
  path is not.
- Start the application with the interpreter of its own virtual environment,
  `.venv/bin/python`, not with the system `python3`: it needs its pinned
  dependencies to validate a signature.
- Do not change the account in `identifiants-lab.txt`: the tests sign in with
  it.

### Two traps that cost others an afternoon

A client created without thinking arrives with the **password grant enabled**.
It is the one grant that defeats the whole point: the application sees the
password again, which is exactly what delegating sign-in was meant to prevent.
Nothing warns you, and the flow works perfectly with it on.

A realm serves a population. The realm of the server's administrators is not
the realm of an application's users. An `issuer` that points at the wrong realm
gives a flow that succeeds, with the wrong people.

```bash
dsoxlab check iam-04-client-oidc-pkce   # grade
dsoxlab hint  iam-04-client-oidc-pkce   # one hint, at the cost of points
```
