# It worked on Friday

Monday morning, the notes application does not let anyone in. Nothing was
deployed over the weekend. Nobody touched anything, which is what everybody
says and is usually true.

Somebody did touch something, and it was probably a two-minute change made with
good intentions: a URL copied from a staging environment, a checkbox clicked
while looking for another one, a client toggled off during a cleanup. These
changes are invisible in any history, because they were made in a console.

You have two sources of truth, and you are going to use both.

The provider **says** what is wrong, on the screen, in a sentence that almost
always names the faulty parameter. People do not read it, because it is wrapped
in a page that says "We are sorry..." and that looks like a generic failure.

The provider also **records** what happened. The realm's event log holds one
line per attempt, with a field that names the cause in a single word:
`invalid_redirect_uri`, `client_disabled`, `invalid_client_credentials`. Reading
that log is faster than any guess.

And there is a third thing, which is why this lab is graded the way it is.

Every one of these faults can be made to disappear without being fixed. Widen
the redirect URI to a wildcard and the error goes away. Turn off PKCE and a
whole class of errors goes away. Open the password grant "just to check" and the
application works again. All of these make the application work on Monday, and
each one leaves a hole that nobody will look at again.

The grading checks that it works. Then it checks, one by one, that you did not
do any of that.
