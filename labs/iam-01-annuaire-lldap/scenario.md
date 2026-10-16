# Before any provider, there is a directory

The identity provider is installed and it works. It has exactly one account in
it: the administrator who installed it. Nobody else exists, so nobody else can
sign in.

That is the normal state of things, and it is where every identity project
begins. A provider does not invent people. It reads them somewhere, and that
somewhere is a directory.

You have LLDAP running on `idp.lab`, with its tree and its administrator. Three
people are joining: Aline in the operations team, Bruno who straddles
operations and auditing, Chloé who only ever reads. Two groups will carry those
roles, and the next lab will teach the provider to read them.

The job sounds like five minutes of LDIF, and it is not, because LLDAP is a
**lightweight** directory. It speaks LDAP, it accepts some writes, and it
refuses others in ways that are not obvious. One of those refusals looks
exactly like a success.

Find out which, and get the memberships in place anyway. Then restart the
container and look again: a directory that forgets is not a directory, and the
only way to know is to try.
