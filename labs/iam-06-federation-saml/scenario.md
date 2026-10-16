# The application that will not speak OIDC

The partner company runs a document management tool. It is old, it works, and
it will outlive everyone involved in this decision. It speaks SAML, and it will
not be speaking anything else: there is no budget for that, and no reason.

Your provider speaks SAML too. Everyone's does, because applications like this
one exist in every company, and they are usually the ones that matter most.

So the two must be introduced to each other, and SAML's way of doing that is
an exchange of **metadata**. Each side publishes a document saying who it is,
where it listens, and which certificate signs what it sends. Neither side
guesses anything about the other.

Then there is the part nobody mentions in the summaries. SAML does not redirect
a browser the way OIDC does. It hands the browser a form and has it submit
itself, twice, and the assertion travels inside it. That is why a SAML
integration cannot be debugged with a redirect trace, and why a browser is
part of the protocol rather than a convenience.

What you are given: your provider with an account and a group, and a second
realm standing in for the partner's tool, empty. What you do: both sides of the
exchange. The client that issues signed assertions, and the identity provider
that consumes them.

Get it wrong in the right way and you will see it: the partner's tool will ask
your user to fill in their own name. That means the assertion arrived, it was
accepted, and it did not say enough.
