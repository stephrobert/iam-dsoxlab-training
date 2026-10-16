# Challenge: one team, not everyone

The realm `formation` holds two groups and two accounts, one in each.
`/opt/iam-lab/identifiants-lab.txt` names them. Both have the same password and
**no second factor at all**.

The application is running on port `9080`.

## What is expected

1. A **copy** of the browser flow is the realm's active browser flow. The flow
   Keycloak provides stays untouched.
2. In that copy, the second factor is required **by role**, and the group
   `devops` carries that role.
3. The condition `conditional-user-configured` is **gone** from the second
   factor's sub-flow.
4. A **phishing-resistant** option is offered alongside the code.
5. The realm's password policy follows NIST SP 800-63B-4: a serious minimum
   length, **no composition rules**, **no expiry**.

## What is proven, and how

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

## Three things measured, and each one costs an afternoon

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

## On the password policy

NIST SP 800-63B-4 asks for length and forbids the rest, and the reason is
measured rather than theoretical. Composition rules produce guessable passwords,
because everyone satisfies the constraint the same way. Periodic expiry produces
incremented variants of the same password. A role attached to the account rather
than the group means one forgotten gesture per arrival.

```bash
dsoxlab check iam-07-mfa-keycloak   # grade
dsoxlab hint  iam-07-mfa-keycloak   # one hint, at the cost of points
```
