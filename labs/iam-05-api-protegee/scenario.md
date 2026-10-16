# The API that trusts every signature

The `notes` API is protected. Someone said so at the last review, and it is
true in a sense: it refuses a call with no token, and it refuses a token whose
signature does not hold. It was tested. It works.

Last week the company added a second API, for invoices. Same provider, same
realm, same keys. A developer wiring the invoice client noticed something while
debugging: the token his client had been issued, meant for the invoice API,
also opened `notes`. Every note, for every user, with a token that was never
intended for this service.

Nothing was broken. No key leaked, no bug in the signature check. The API
simply never asked the one question that mattered: **is this token for me?**

A signature proves where a token comes from. It says nothing about who it is
for, nor whether it is still valid, nor what its holder is allowed to do. Those
are three separate claims, and an API that skips them is open to anyone holding
any token from the same provider.

You have the API, in that exact state, running on `idp.lab`. You also have a
second API declared beside it, for one purpose: to issue you a token that is
perfectly valid and simply not yours. Use it. Watch the API accept it.

Then close it, and while you are there, the backup service needs access too.
It has no user, it runs at three in the morning, and it only ever reads. Give
it exactly that, and nothing more: an unwatched machine account that can write
is how data disappears quietly.
