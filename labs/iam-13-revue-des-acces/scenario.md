# Nobody remembers why he has it

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
