# Fifteen consultants, and no accounts for them

The partner company is sending fifteen consultants for six months. They need
access to three of your applications, and they already have accounts: with
their own employer, who manages their passwords, their two-factor devices and,
most importantly, their departures.

You could create fifteen accounts. Everyone does, the first time. Then someone
leaves the partner company in March, nobody tells you, and their account works
until the day someone thinks to ask.

The other way is to let their employer answer for them. Your realm becomes a
**broker**: when a consultant signs in, it sends them to the partner, the
partner authenticates them, and your realm creates a local account linked to
that answer. The password never comes to you, and the day the consultant leaves
the partner company, the partner's refusal is your refusal.

That part is straightforward, and it is not where the afternoon goes.

The afternoon goes into the question nobody asks out loud: **what does a
stranger get, exactly, on arrival?** An account with no group has no rights and
is useless. An account placed by hand has whatever the person who placed it
remembered. And an account that arrives with an administration role is a door
nobody will ever look at again.

There is one more thing, and it is the sharp edge of this whole lab. Your realm
already holds an account with the same email address as one of the partner's
people. Email addresses collide: people change jobs, companies merge, somebody
mistyped something in 2019. If your first-login flow treats a matching address
as proof of identity, then the stranger from the partner company is now that
person. No alert, no trace, nothing to notice.

Two of the partner's people will sign in during the grading. One must get in.
One must not.
