# Nobody remembers why he has it

## The situation

The quarterly access review arrives as a spreadsheet. Someone exports the list
of accounts, someone else ticks the boxes, and a third person signs it. It
takes an afternoon and it finds nothing, every quarter.

It finds nothing because of how it is built. The export lists accounts and
their groups, because that is what the console shows on one screen. Groups are
the clean part: they have names, owners, a reason for existing.

The dirty part is elsewhere. Someone needed production access on a Tuesday in
March, during an incident. It was granted directly to their account, not
through a group, because a group would have taken a ticket and two approvals
and the incident was happening now. It worked. It was never removed. It appears
in no group listing, and the review that lists groups has signed it off three
times.

You have that exact situation: three accounts, two groups, and a role granted
to someone directly, with a description that says what happened and admits
there was no ticket.

Two other things need doing while you are here, and both are about doing less
by hand.

The arrival of a new colleague should not be a form someone fills in. The
provider has a provisioning API, closed by default, that a tool can call. Open
it, give it a client that can do exactly that and nothing else, and create
somebody with it.

And the departure of someone who simply stops coming should not wait for a
review either. The provider can run a workflow on a schedule. Write the one
that disables an idle account, and pay attention to the verb: there is an
option that deletes, and it would destroy the evidence along with the access,
on its own, at three in the morning.

## Provision, automate, and find what the review misses

The realm `formation` holds three accounts and two groups.
`/opt/iam-lab/identifiants-lab.txt` names them, names the role granted
directly, says who holds it, and gives the SCIM URL and where to write the
review.

The SCIM API is **closed**, and there is **no workflow**. The setup checks both
before handing over.

### What is expected

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

### Three things measured, each one an afternoon

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

### On the workflow

The API takes a name and steps, and it **returns YAML**, not JSON, which is
worth knowing before you try to parse its answer. A `POST {}` tells you what it
wants.

The verb matters more than the syntax. There is a step that deletes, and the
grading refuses it: a lifecycle rule that destroys accounts destroys the
evidence too, and it does so unattended.

### On the review

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
