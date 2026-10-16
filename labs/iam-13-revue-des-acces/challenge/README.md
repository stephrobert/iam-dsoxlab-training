# Challenge: provision, automate, and find what the review misses

The realm `formation` holds three accounts and two groups.
`/opt/iam-lab/identifiants-lab.txt` names them, names the role granted
directly, says who holds it, and gives the SCIM URL and where to write the
review.

The SCIM API is **closed**, and there is **no workflow**. The setup checks both
before handing over.

## What is expected

1. The **SCIM API is open** on the realm, and answers `401` without a token
   rather than `404`.
2. A client named **`scim-client`** exists: confidential, with a service
   account, no authorization code flow, and holding only what it needs on
   accounts. Not `realm-admin`.
3. That client's token is **accepted** by the SCIM API.
4. The account named in `COMPTE_A_PROVISIONNER` has been created **through the
   API**, and can be read back through it.
5. A **workflow** exists that **disables** an account. Not one that deletes.
6. The review file lists every account with its groups **and its roles**, and
   the unjustified role has been **removed**, from the realm and from the
   review.

## Three things measured, each one an afternoon

**The feature is enabled on the server and the API still answers 404.** It
opens per realm, and the flag lives at the **root** of the realm's
representation. Put it in the realm's `attributes` and the update returns `204`
while the value reads back as false. Nothing reports it.

**Once open, it answers 401 with SCIM-shaped messages.** The realm `master`
administrator's token gets « Bearer token required ». A client token from this
realm gets « Invalid token audience ».

**The audience it wants is the API's own URL.** Three plausible candidates were
tried before that one. Giving a token an audience is the mapper from lab 05,
used again.

## On the workflow

The API takes a name and steps, and it **returns YAML**, not JSON, which is
worth knowing before you try to parse its answer. A `POST {}` tells you what it
wants.

The verb matters more than the syntax. There is a step that deletes, and the
grading refuses it: a lifecycle rule that destroys accounts destroys the
evidence too, and it does so unattended.

## On the review

Same shape as the one in lab 8: JSON, one entry per account, each with a
`username`, a groups key and a `roles` key. It must be complete, and it must
describe the state **after** your work.

What is graded beyond that is whether you **found** the thing. The review is not
there to be signed, it is there to find an access nobody can justify and to
remove it.

```bash
dsoxlab check iam-13-revue-des-acces   # grade
dsoxlab hint  iam-13-revue-des-acces   # one hint, at the cost of points
```
