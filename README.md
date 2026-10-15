# iam-dsoxlab-training

**Language:** [English](./README.md) · [Français](./README.fr.md)

Verifiable labs for the blog's
[identity and access management course](https://blog.stephane-robert.info/docs/services/identite/).
They are played by the [dsoxlab](https://github.com/stephrobert/dsoxlab) CLI,
which lives elsewhere: this repository is only a content provider.

> **Status: under construction.** The catalog skeleton is in place, no lab is
> written yet. The sixteen specifications that describe them live under
> `preparation/fiches/`. A lab enters `meta.yml` the day it is written **and**
> played, not before.

## Why this repository exists

An IAM course can be taught entirely on paper: flow diagrams, protocol names,
screenshots of an admin console. Learners come out recognising the vocabulary,
having never seen a token refused for the right reason.

Yet nothing in this field is proven by reading. A misconfigured OIDC client
returns a token that looks like a valid token. An API that does not check the
audience accepts a token issued for someone else. A logout that closes the
session leaves the old access token valid until it expires. Those three facts
take one command each to witness and are never forgotten afterwards; explained,
they slip away.

So this catalog gives learners the means to **check themselves**, against a
real identity provider, with real applications.

## The rule that governs everything else

**A lab is graded on the state of the system, never on the commands typed.**

Learners reach the result by whatever path they choose. The tests therefore
question Keycloak through its administration API and its OIDC endpoints, the
directory through LDAP, and the witness applications through their own
responses.

```python
# NO: we re-read what the learner wrote, which proves nothing
assert "pkce" in config_read

# YES: we ask the provider what it actually requires
client = admin.get(f"/admin/realms/{realm}/clients/{id}")
assert client["attributes"]["pkce.code.challenge.method"] == "S256"
```

And a lab is proven **in both directions**: after `dsoxlab run`, `dsoxlab check`
must return **0**, since the work has not been done. After the reference
solution, it must return **100**. A test that passes before the work measures
nothing, and it is this field's most expensive defect.

## Playing a lab

```bash
export LAB_HOME=$PWD
dsoxlab use --provider kvm     # a list of providers does not resolve on its own
dsoxlab provision              # creates the machine, once
dsoxlab list-labs              # the catalog
dsoxlab run   <id>             # lays down the initial state and opens the session
dsoxlab check <id>             # runs the tests and computes the score
dsoxlab hint  <id>             # one hint, at the cost of points
dsoxlab clean <id>             # undoes the lab, keeps the machine
dsoxlab destroy                # gives the machine back
```

## The machine, and why only one

One virtual machine, declared in `meta.yml` and provisioned by
`dsoxlab provision`:

| Host | Distribution | vCPU | RAM | Disk |
|---|---|---|---|---|
| `idp.lab` | Ubuntu 24.04 | 2 | 6 GB | 30 GB |

Everything runs there in containers: Keycloak, its PostgreSQL database, the
LLDAP directory, the witness application and the witness API. Two labs need
more than that, and they are what sets 6 GB rather than the 4 GB minimum:

- `iam-11-federation-externe` starts a **second Keycloak**, playing the partner
  company's identity provider. An account with a public provider would make the
  lab unplayable offline and dependent on a service nobody controls;
- `iam-14-plateforme` brings up a **k3d cluster inside the machine**, to wire
  its API server to the identity provider.

Nothing runs on the learner's own machine: an identity provider listening on
the working machine eventually collides with something else, and that is not
what the lab teaches.

## The path

Two levels, in playing order. It does not follow the numbering of the
specifications: labs 11 and 12 are played in module 4, 13 in module 6, 14 in
module 7.

### Level 1: wire an application to an identity provider

Install Keycloak with its database, wire an application in OIDC with PKCE, put
an API behind access tokens, federate a directory then a SAML service, broker an
external provider, and diagnose a broken integration. Ends with the level exam.

### Level 2: run and govern

Enforce strong authentication, handle a leaving employee, review access, wire
the platform in, back up and upgrade the provider, and describe the realm as
code. Ends with the final exam.

## Solutions are encrypted

Learners must search. Reference solutions therefore live under
`solution/<lab>/`, encrypted with `ansible-vault`, and the password
(`.vault-pass` at the root) is never versioned. A solution file in clear text is
a defect, which `tests/test_solutions_chiffrees.py` refuses.

A lab's tutorial never gives its answer away either: it teaches each mechanism
on a throwaway example, deliberately named outside the challenge's subject, that
the learner then has to carry over.

## This repository is not the CLI

An engine defect is fixed in [dsoxlab](https://github.com/stephrobert/dsoxlab),
or reported as an issue. Here, everything driving the CLI is declarative:
`meta.yml` for the catalog, `lab.yaml` per lab, `setup.yaml` and `cleanup.yaml`
for the machine, `challenge/tests/test_functional.py` for the proof.

## License

[CC BY 4.0](./LICENSE).
