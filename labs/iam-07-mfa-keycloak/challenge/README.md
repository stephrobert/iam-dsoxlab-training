# The team that can lock everyone out

## The situation

The operations team has keys to everything. Four people, each with a password,
and that password is the only thing between a phishing email and your
production.

The decision came down from the audit: second factor for operations. Nobody
disagrees.

The way it goes wrong is almost always the same, and it goes wrong in one of two
directions.

**Too wide.** Someone requires the second factor from everyone, on the default
flow, and discovers on Monday that the administrator account has no second
factor either. Nobody can get in to undo it. The flow that was modified was the
one Keycloak provides, so there is nothing to roll back to.

**Too narrow.** Someone requires it with the condition Keycloak suggests first,
which reads "user configured". It means: ask for a second factor from people who
have one. The four people in operations have none. They sign in exactly as
before, the setting looks right in the console, and the audit is told it is
done.

The second one is worse, because nothing tells you. There is no error, no
warning, and the console shows a flow with the second factor in it.

You have two accounts, in two teams, with the same password and no second
factor at all. One must be stopped. The other must go through. That is the whole
test, and it is the only one that cannot be fooled.

While you are in there, the password policy needs attention too. The current
one is whatever Keycloak ships with, and the standard it should follow says
something that surprises most people: length, and nothing else. No composition
rules, no expiry.

## One team, not everyone

The realm `formation` holds two groups and two accounts, one in each.
`/opt/iam-lab/identifiants-lab.txt` names them. Both have the same password and
**no second factor at all**.

The application is running on port `9080`.

### What is expected

1. A **copy** of the browser flow is the realm's active browser flow. The flow
   Keycloak provides stays untouched.
2. In that copy, the second factor is required **by role**, and the group
   `devops` carries that role.
3. The condition `conditional-user-configured` is **gone** from the second
   factor's sub-flow.
4. A **phishing-resistant** option is offered alongside the code.
5. The realm's password policy follows NIST SP 800-63B-4: a serious minimum
   length, **no composition rules**, **no expiry**.

### What is proven, and how

Seven tests. The one that decides everything plays **two sign-ins**:

| Account | Its team | Expected |
|---|---|---|
| `resp-exploitation` | `devops` | **stopped**, on a screen asking to set up a second factor |
| `resp-lecture` | `lecteurs` | **goes through** |

Both have the same password and no second factor. Only their membership
differs, so only their membership can explain the difference.

The other tests check the flow Keycloak provides is intact, that the active flow
is a copy, that the condition is a role and not `user configured`, that the role
is on the **group** and not on the account, that a phishing-resistant option is
offered, and the password policy.

### Three things measured, and each one costs an afternoon

**Keycloak 26.8.1 has no group condition.** The available conditions are role,
user attribute, credential, user configured, client scope, level of
authentication, and sub-flow executed. Targeting a team goes through a **role**,
which the group carries.

**`conditional-user-configured` is the trap.** With it in place, the second
factor is only demanded from people who already have one. Measured: an account
with no second factor signs in directly, even with the OTP step set to
`REQUIRED`. Nothing reports it.

**A copy of the browser flow contains two conditional sub-flows**, each with its
own `conditional-user-configured`. The one under *Conditional Organization* has
nothing to do with the second factor and must stay. Remove the wrong one and the
trap is still there.

### On the password policy

NIST SP 800-63B-4 asks for length and forbids the rest, and the reason is
measured rather than theoretical. Composition rules produce guessable passwords,
because everyone satisfies the constraint the same way. Periodic expiry produces
incremented variants of the same password. A role attached to the account rather
than the group means one forgotten gesture per arrival.

```bash
dsoxlab check iam-07-mfa-keycloak   # grade
dsoxlab hint  iam-07-mfa-keycloak   # one hint, at the cost of points
```
