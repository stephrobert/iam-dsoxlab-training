# IAM Training: wire an application to an identity provider, then run it

**Language:** [English](./README.md) · [Français](./README.fr.md)

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](./LICENSE)

Verifiable labs for the blog's
[identity and access management course](https://www.stephane-robert.info/docs/services/identite/),
played with [dsoxlab](https://github.com/stephrobert/dsoxlab).

## What it is

**Sixteen labs, one identity provider, and the densest test suite of the whole
collection.** An IAM course can be taught entirely on paper: flow diagrams,
protocol names, screenshots of an admin console. Learners come out recognising
the vocabulary, having never seen a token refused for the right reason.

Yet nothing in this field is proven by reading. A misconfigured OIDC client
returns a token that looks like a valid token. An API that does not check the
audience accepts a token issued for someone else. A logout that closes the
session leaves the old access token valid until it expires. Those three facts
take one command each to witness and are never forgotten afterwards; explained,
they slip away.

So this catalog gives learners the means to **check themselves**, against a real
identity provider, with real applications.

### The rule that governs everything else

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

## Requirements

- **Python 3.11+ and [`uv`](https://docs.astral.sh/uv/)**
- **`git`**
- **A hypervisor**, because every lab here is `runtime: vm`: either
  **libvirt/KVM** (with `terraform` and the `dmacvicar/libvirt` provider) or
  **Incus**. The provider is declared as a list in [`meta.yml`](./meta.yml),
  and **a list does not resolve on its own**: pick one with
  `dsoxlab use --provider kvm`.
- **6 GB of free RAM and 30 GB of disk** for the single machine, `idp.lab`.
  Two labs are what set 6 GB rather than the 4 GB minimum, and the next section
  says which.
- **Outbound network access** on first provision, to pull the base image and
  the container images.

`dsoxlab doctor` says what this repository needs and what it does not, and
tells apart a check that failed from one it could not measure.

### The machine, and why only one

One virtual machine, declared in `meta.yml` and provisioned by
`dsoxlab provision`:

| Host | Distribution | vCPU | RAM | Disk |
|---|---|---|---|---|
| `idp.lab` | Ubuntu 24.04 | 2 | 6 GB | 30 GB |

Everything runs there in containers: Keycloak, its PostgreSQL database, the
LLDAP directory, the witness application and the witness API. Two labs need
more than that:

- `iam-11-federation-externe` starts a **second Keycloak**, playing the partner
  company's identity provider. An account with a public provider would make the
  lab unplayable offline and dependent on a service nobody controls;
- `iam-14-plateforme` brings up a **k3d cluster inside the machine**, to wire
  its API server to the identity provider.

Nothing runs on the learner's own machine: an identity provider listening on
the working machine eventually collides with something else, and that is not
what the lab teaches.

## Install

`dsoxlab` is published on [PyPI](https://pypi.org/project/dsoxlab/). Install it
as a standalone tool, so it stays out of this repository:

```bash
# 1. The dsoxlab CLI (external tool, stays out of this repo)
uv tool install dsoxlab

# 2. This lab catalog
git clone https://github.com/stephrobert/iam-dsoxlab-training.git
cd iam-dsoxlab-training

# 3. Check the contract and the machine
dsoxlab validate-structure
dsoxlab doctor
```

### Your first lab, in five minutes

The machine has to exist first: nothing here runs on your own host.

```bash
export LAB_HOME=$PWD
dsoxlab use --provider kvm           # a list of providers does not resolve on its own
dsoxlab provision                    # creates idp.lab, once

dsoxlab list-labs                    # the sixteen labs, in playing order
dsoxlab run       iam-02-keycloak-installer
dsoxlab challenge iam-02-keycloak-installer
dsoxlab check     iam-02-keycloak-installer

dsoxlab clean     iam-02-keycloak-installer   # undoes the lab, keeps the machine
dsoxlab destroy                               # gives the machine back
```

`provision` exits non-zero if a host does not answer, and names the orphan
domains it left behind rather than claiming success. Running `check` on a lab
you never started measures nothing, and says so rather than recording a 0.

### Keeping it up to date

```bash
uv tool upgrade dsoxlab        # the engine, published on PyPI
git -C <this repo> pull        # the catalog
```

The engine and the catalog move independently: a new `dsoxlab` never requires
re-cloning the labs, and new labs never require upgrading the tool, as long as
the contract version matches.

## How it works

### The declarative contract (two levels)

This repository is **not the CLI**. An engine defect is fixed in
[dsoxlab](https://github.com/stephrobert/dsoxlab), or reported as an issue
there. Here, everything driving the CLI is declarative:

- **`meta.yml`** at the root declares the repository identity, the
  **infrastructure** (provider, network `lab-iam`, `10.10.80.0/24`, and the
  single host `idp.lab`) and the **order** of the sections shown by
  `list-labs`;
- **`lab.yaml`** per lab declares its `skills`, `level`, `runtime` (type and
  targets), `distros`, `doc_url` and a `validation` block. A `lab.fr.yaml`
  overrides `title` and `description` in French, and nothing else;
- **`setup.yaml`** and **`cleanup.yaml`** lay down and undo the machine state;
- **`challenge/tests/test_functional.py`** carries the proof.

The Terraform and cloud-init templates are **packaged inside dsoxlab**, not
here: this repository declares only its `infra:` block and its public key in
`ssh/`.

### The lab lifecycle

```bash
dsoxlab list-labs              # browse the catalog
dsoxlab show      <id>         # metadata and status of one lab
dsoxlab run       <id>         # lay down the initial state and open the session
dsoxlab challenge <id>         # read the mission, no step-by-step
dsoxlab hint      <id>         # reveal a hint (deducted from the score)
dsoxlab check     <id>         # run the tests, compute and record the score
dsoxlab clean     <id>         # undo the lab, keep the machine
dsoxlab progress               # per-section progress, average score
```

### Runtimes

| Runtime | What the lab asks for |
|---|---|
| `vm` | the `idp.lab` machine, provisioned by `dsoxlab provision`, on Ubuntu 24.04. Keycloak, PostgreSQL, LLDAP and the witness applications run there as containers, started by the lab's `setup.yaml`. |

All sixteen labs are `vm`, and none declares `runtime.services`: the containers
belong to the machine, not to the learner's host, so they are brought up inside
it by Ansible rather than by dsoxlab.

### The validation model

Validation **proves the state, it does not trust the learner**, and a lab is
proven **in both directions**: after `dsoxlab run`, `dsoxlab check` must return
**0**, since the work has not been done. After the reference solution, it must
return **100**. A test that passes before the work measures nothing, and it is
this field's most expensive defect.

With 544 assertions for sixteen labs, this is the densest catalog of the
collection: every mechanism is questioned where it actually lives, through
Keycloak's administration API, its OIDC endpoints, LDAP, and the witness
applications' own responses.

### Solutions are encrypted

Learners must search. Reference solutions therefore live under
`solution/<lab>/`, encrypted with `ansible-vault`, and the password
(`.vault-pass` at the root) is never versioned. A solution file in clear text
is a defect, which [`tests/test_solutions_chiffrees.py`](./tests/) refuses.

A lab's tutorial never gives its answer away either: it teaches each mechanism
on a throwaway example, deliberately named outside the challenge's subject,
that the learner then has to carry over.

### Scoring, hints, progress

`check` records a score (tests passed out of total, minus the cost of any hints
revealed). Hints are **base64-encoded** in `challenge/hints.yaml`, so that
opening the file does not give them away, and their cost grows with their
precision. History lives in a SQLite database **local to this repository**.

A run that measured nothing is neither a pass nor a failure: if every collected
test skips, `check` records no score and says why. A score of 0 would accuse
the lab of what is missing from the machine, which here is usually `idp.lab`
not being up.

## Catalog

Two levels, in **playing order**. It does not follow the numbering of the
specifications: labs 11 and 12 are played in module 4, 13 in module 6, 14 in
module 7.

### Level 1: wire an application to an identity provider

Install Keycloak with its database, wire an application in OIDC with PKCE, put
an API behind access tokens, federate a directory then a SAML service, broker an
external provider, and diagnose a broken integration. Ends with the level exam.

| Lab (id) | Title | Type | Companion guide |
|---|---|---|---|
| `iam-02-keycloak-installer` | Install Keycloak with its database | lab | [guide](https://www.stephane-robert.info/docs/services/identite/keycloak/installation/) (in French) |
| `iam-04-client-oidc-pkce` | Connect an application with OIDC and PKCE | lab | [guide](https://www.stephane-robert.info/docs/services/identite/keycloak/securiser-application-oidc/) (in French) |
| `iam-05-api-protegee` | Put an API behind access tokens | lab | [guide](https://www.stephane-robert.info/docs/services/identite/keycloak/proteger-une-api/) (in French) |
| `iam-01-annuaire-lldap` | Organise accounts and groups in a directory | lab | [guide](https://www.stephane-robert.info/docs/services/identite/lldap/) (in French) |
| `iam-03-federation-ldap` | Federate a directory into the provider | lab | [guide](https://www.stephane-robert.info/docs/services/identite/keycloak/federation-ldap/) (in French) |
| `iam-06-federation-saml` | Federate an application over SAML | lab | [guide](https://www.stephane-robert.info/docs/services/identite/fondamentaux/saml/) (in French) |
| `iam-11-federation-externe` | Broker an external identity provider | lab | [guide](https://www.stephane-robert.info/docs/services/identite/keycloak/federation-entrante/) (in French) |
| `iam-12-depanner-integration` | Repair an integration that stopped working | lab | [guide](https://www.stephane-robert.info/docs/services/identite/keycloak/depanner-integration/) (in French) |
| `iam-epreuve-n1` | Level 1 exam: stand up a provider, federate, wire an app and an API | capstone | [guide](https://www.stephane-robert.info/docs/services/identite/epreuve-niveau-1/) (in French) |

### Level 2: run and govern

Enforce strong authentication, handle a leaving employee, review access, wire
the platform in, back up and upgrade the provider, and describe the realm as
code. Ends with the final exam.

| Lab (id) | Title | Type | Companion guide |
|---|---|---|---|
| `iam-07-mfa-keycloak` | Require a second factor, for some people only | lab | [guide](https://www.stephane-robert.info/docs/services/identite/keycloak/mfa-flows/) (in French) |
| `iam-08-depart-collaborateur` | Cut off someone who is leaving | lab | [guide](https://www.stephane-robert.info/docs/services/identite/keycloak/revue-des-acces/) (in French) |
| `iam-13-revue-des-acces` | Automate the lifecycle, and conduct a real review | lab | [guide](https://www.stephane-robert.info/docs/services/identite/keycloak/revue-des-acces/) (in French) |
| `iam-14-plateforme` | Make a cluster and a tool authenticate against the provider | lab | [guide](https://www.stephane-robert.info/docs/services/identite/keycloak/plateforme/) (in French) |
| `iam-09-sauvegarde-montee-version` | Back up what must be, upgrade, and prove nothing was lost | lab | [guide](https://www.stephane-robert.info/docs/services/identite/keycloak/production/) (in French) |
| `iam-10-realm-as-code` | Describe a realm as code, apply it, and catch the drift | lab | [guide](https://www.stephane-robert.info/docs/services/identite/keycloak/configuration-as-code/) (in French) |
| `iam-epreuve` | Final exam: an identity, end to end | capstone | [guide](https://www.stephane-robert.info/docs/services/identite/epreuve-niveau-2/) (in French) |

_16 labs. This catalog has no `scripts/gen_catalog.py` yet, so these tables are
maintained by hand: check them against `dsoxlab list-labs` when you add a lab._

## Contributing

A lab is proven **in both directions** before it is merged,
`dsoxlab validate-structure` is green, and the statement exists in English and
in French. A lab enters `meta.yml` the day it is written **and** played, not
before.

Anything user-facing is bilingual. A document translated on one side only is
reported by the validator, not left to goodwill.

## License

See [`LICENSE`](./LICENSE) (CC BY 4.0).
