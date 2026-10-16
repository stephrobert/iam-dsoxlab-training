# The application that must stop holding passwords

The `notes` application asks its users for a login and a password, checks them
against its own table, and keeps a session. It works. It has worked for six
years.

Then the company bought a second tool, and a third. Each one asks for a password.
Each one keeps its own table. When someone leaves, three tables have to be
updated, and the day someone forgets one, a former employee still reads the
notes.

You have an identity provider running: Keycloak, with its database, on
`idp.lab`. The decision is made, and it is not up for discussion: `notes`
stops asking for passwords. It sends the user to the provider, and the provider
sends them back with proof of who they are.

That proof is a token, and a token is only worth the checks made on it. The
witness application already knows how to make them, all of them. What it does
not know is **who it should talk to**, and the provider does not yet know that
this application exists.

This is the whole job: declare the application to the provider, declare the
provider to the application, and leave nothing open that should be closed.

What you will be graded on is not your configuration file. It is what the
provider **refuses**: a code exchanged without proof of origin, a return address
that was never declared, a password grant that would let the application see the
password again. An integration that works and refuses nothing is an integration
that has not been done.
