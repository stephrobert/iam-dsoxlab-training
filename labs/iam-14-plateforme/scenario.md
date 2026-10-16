# The cluster has its own list of who you are

Access to the cluster works by certificate. Each person who needs `kubectl` has
been handed a key and a certificate, generated once, by whoever was on duty
that day. The files were sent over chat. They do not expire in any useful
sense, and nobody knows who holds a copy.

When somebody leaves, their directory account is disabled within the hour. The
certificate keeps working. There is no list of issued certificates, and there
is no way to revoke one: the cluster has no revocation to check. The only
honest fix is to rotate the certificate authority, which invalidates everyone
at once, which is why it has never been done.

The cluster, in other words, has its own list of who people are, and that list
drifts away from the directory from the moment it is written.

You are going to replace it. The cluster can be told to trust the identity
provider instead: a person runs `kubectl`, gets a token from the provider, and
the cluster reads it. Leaving the company then closes the cluster too, because
there is only one place where accounts live.

Two things have to be true for that to be worth doing.

The rights must follow the **group**, not the person. If you bind rights to
usernames, you have rebuilt the drift somewhere else, in a file this time. And
the group must be bound to something **bounded**: there is a role that grants
the entire cluster, it would make the lab pass, and it would hand the machine
to whoever can get themselves added to a group in the directory, which is not
a decision the cluster gets to review.

While you are at it, the platform's dashboard needs the same treatment, for the
same reason: it has its own local accounts, and three of them belong to people
who left.

One warning about this lab, which is not about identity at all. A cluster's API
server refuses to trust a provider over plain HTTP, and it refuses by not
starting, with the reason in a log you have to go and read. The setup has
already placed a TLS access in front of the provider so that you can do the
work. Keep in mind that the provider now answers on two doors, and that it does
not say the same thing about itself on each one.
