# Somebody changed something

## The situation

The realm works. It took three weeks of console clicks to get there, spread
over four months, by five people, and it works. Nobody can say what it
contains. There is a wiki page listing the clients, written in March, and two
of those clients no longer exist.

Last Tuesday something stopped working for one application, and the
investigation found that a token lifetime had been changed from ten minutes to
thirty. The change is in the admin event log, with a date and an account name.
The account belongs to somebody who no longer works here, and the log says what
was changed, not why.

That is the real cost of a configuration that lives only in the server: not
that it drifts, but that nothing can distinguish a deliberate change from a
mistake. Both appear the same way, both are already in production, and the only
record of intent is somebody's memory.

So you are going to write it down instead. Not in a wiki page, which drifts
without telling anybody, but in files that a tool reads and enforces, so that
the question « what should this realm contain » has a single answer, and the
question « has anybody changed it » can be answered by a command rather than an
investigation.

You will describe a small realm: two roles, a group, a public client and a
confidential one. Then you will apply it, change something by hand the way
Tuesday's change was made, and watch the files take the realm back.

Two warnings, both about what « versioned » implies.

A confidential client has a secret. Not writing that secret in your files is
the obvious move, and it is not sufficient: the tool keeps a record of
everything it manages, and that record is a file on disk with default
permissions. Go and look at it before you decide you are done.

And the tool authenticates somewhere in order to do its work. That somewhere is
a realm, and it is not the realm you are describing. Confuse the two and you
will apply your specification to the administrative realm, or to the one the
other labs depend on, and the grading checks both.

## Describe the realm, apply it, catch the drift

`/opt/iam-lab/identifiants-lab.txt` **is the specification**. It names the
realm to create, its display name, its token lifetime in seconds, its roles,
its group, both client ids, the name of the variable that must carry the
confidential client's secret, the working directory, and the provider version
to pin. The tests read those values from that file: nothing is hard-coded on
either side.

Terraform is installed. The working directory is empty. The realm does not
exist.

### What is expected

1. `.tf` files in the working directory that **pin the provider version**, and
   a state file: the realm must be described, not merely created.
2. The realm existing with the display name and the token lifetime specified,
   plus both roles, the group, and both clients.
3. The public client requiring **PKCE S256**.
4. `terraform plan -detailed-exitcode` returning **0**: what runs is what is
   written.
5. A drift introduced by hand being **corrected** by applying again. The test
   introduces one itself, checks that the plan returns **2**, applies, and
   checks the value came back.
6. **No credential in clear** in anything you wrote. The test reads the
   socle's admin password and the client's actual secret from the API, then
   greps your files for both.
7. The working directory **closed to others**, because of what the state file
   contains.
8. The `master` and `formation` realms untouched.

### Where the credentials go

The provider reads `KEYCLOAK_URL`, `KEYCLOAK_USER`, `KEYCLOAK_PASSWORD` and
`KEYCLOAK_REALM` from the environment. Nothing needs to be written in a file.
The socle's admin account is in `/opt/socle-iam/.env`.

The confidential client's secret goes through a Terraform variable, whose name
the specification fixes (`VARIABLE_SECRET_ATTENDUE`), passed as
`TF_VAR_<name>`. The name is imposed because the grading replays your code and
has to be able to feed it.

### Three things measured on this machine

**The provider announces itself as « self-signed » at `terraform init`**, with
its key fingerprint. That is not a warning: it is the signature of a publisher
who is not HashiCorp. The provider lives under the `keycloak` organisation on
GitHub.

**`plan -detailed-exitcode` returns 0 when the state matches, 2 when it
differs, 1 on error.** Judge with the code, not by reading the output.

**The state file keeps your secret in clear, and its backup is recreated with
default permissions on every apply.** So `terraform.tfstate` keeps whatever
mode you give it, because the tool writes into the existing file, while
`terraform.tfstate.backup` comes back as `644` every single time. Protecting
the file does not hold. Protecting the directory does.

### Two failure cases the grading catches

**A secret written in clear**, admin password or client secret, in a `.tf` or a
`.tfvars`. The test knows the real values: it does not look for the word
« password », it looks for the value.

**The specification applied to the wrong realm.** The provider authenticates
against one realm and manages another. Every resource's `realm_id` must point
at the realm you are describing.

```bash
dsoxlab check iam-10-realm-as-code   # grade
dsoxlab hint  iam-10-realm-as-code   # one hint, at the cost of points
```
