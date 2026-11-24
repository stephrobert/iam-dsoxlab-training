# The API that trusts every signature

## The situation

The `notes` API is protected. Someone said so at the last review, and it is
true in a sense: it refuses a call with no token, and it refuses a token whose
signature does not hold. It was tested. It works.

Last week the company added a second API, for invoices. Same provider, same
realm, same keys. A developer wiring the invoice client noticed something while
debugging: the token his client had been issued, meant for the invoice API,
also opened `notes`. Every note, for every user, with a token that was never
intended for this service.

Nothing was broken. No key leaked, no bug in the signature check. The API
simply never asked the one question that mattered: **is this token for me?**

A signature proves where a token comes from. It says nothing about who it is
for, nor whether it is still valid, nor what its holder is allowed to do. Those
are three separate claims, and an API that skips them is open to anyone holding
any token from the same provider.

You have the API, in that exact state, running on `idp.lab`. You also have a
second API declared beside it, for one purpose: to issue you a token that is
perfectly valid and simply not yours. Use it. Watch the API accept it.

Then close it, and while you are there, the backup service needs access too.
It has no user, it runs at three in the morning, and it only ever reads. Give
it exactly that, and nothing more: an unwatched machine account that can write
is how data disappears quietly.

## An API that asks the right questions

The provider runs on `idp.lab`, port `8080`, realm `formation`. The API runs on
port `8090`, from `/opt/iam-lab/api-notes/api.py`, and it is already started.

`/opt/iam-lab/identifiants-lab.txt` holds the test account and the names of the
objects the setup placed for you.

### What is already there, and what it is for

| Name | What it is |
|---|---|
| `notes-cli` | a public client with the direct grant, so you can get tokens from the command line |
| `autre-api` | a second API, declared for one purpose: to be an audience that is not yours |
| `autre:lecture` | its scope, which carries its audience. Ask for it and you get a valid token meant for someone else |
| `alice` | the human account of the lab |

Start by using them. Get a token with `autre:lecture`, call `GET /notes` with
it, and watch the API answer `200`. That is the state you are fixing.

### What is expected

1. The API is declared as a **client** named **`notes-api`**, with no flow at
   all. Its client id is what tokens will name as their audience.
2. Two **scopes** exist, `notes:lecture` and `notes:ecriture`, one per
   permission. Each one carries the **audience** of `notes-api`.
3. The API checks **four** claims, not one: signature, issuer, audience and
   expiry. Then it checks the **scope** that the route requires.
4. A **backup service** has machine access: a confidential client named
   **`service-sauvegarde`**, with a service account, holding **read only**.
5. The service's secret is written in **no file**.

### What is proven, and how

The tests do not read your code. They send tokens and read what the API
answers:

- no token, `401` with a `WWW-Authenticate` header;
- a token with the right audience and scope, `200`;
- a token meant for `autre-api`, `401`;
- a read-only token on a write, `403` naming `insufficient_scope`;
- the service's token, `200` on read and `403` on write.

The distinction between `401` and `403` is graded, and it is not cosmetic.
`401` says "I do not know who you are", and a client retries with credentials.
`403` says "I know who you are, and it is not enough", and retrying is
pointless.

### Constraints

- The names are fixed: `notes-api`, `service-sauvegarde`, `notes:lecture`,
  `notes:ecriture`. The tests look them up.
- `GET` requires read, `POST` requires write.
- Start the API with the interpreter at
  `/opt/iam-lab/appli-temoin/.venv/bin/python`, which has the pinned
  dependencies. The system `python3` has no JWT library.
- Do not touch `autre-api` or `notes-cli`: they are the measuring instruments.

### Two traps that cost others an afternoon

**A scope does not change the audience.** Declaring `notes:lecture` puts
nothing in `aud`. The audience arrives through a protocol mapper on the scope,
which names the client it targets. Without it, tokens stay addressed to
`account`, and the API cannot tell they are for it. This is the single point
that stops most people.

**A service has nobody to ask for a scope.** Under client credentials, only
the client's **default** scopes end up in the token. Attach the read scope as
optional and the service gets a token with no permission at all, while every
test about users keeps passing.

```bash
dsoxlab check iam-05-api-protegee   # grade
dsoxlab hint  iam-05-api-protegee   # one hint, at the cost of points
```
