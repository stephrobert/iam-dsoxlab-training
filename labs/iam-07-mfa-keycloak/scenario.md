# The team that can lock everyone out

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
