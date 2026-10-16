# Two lists of people, and nobody knows which one is right

The directory holds the company's accounts. The identity provider holds its
own. Both were filled in by hand, a few weeks apart, and they have been
drifting ever since.

Someone left in July. They are gone from the directory. They still sign in
through the provider.

Somebody's surname was corrected in the directory. The provider still shows the
old one on every screen, and nobody can say which is the real one, because both
are equally authoritative and equally wrong.

There is only one way out of this, and it is not a synchronisation script. The
provider must stop holding a copy, and start **reading** the directory. One
source, one truth, and a deletion that takes effect everywhere because there is
only one place to delete from.

Keycloak can do that. It federates a directory: it reads the accounts, imports
them so it can attach groups and sessions to them, and refuses to write back.
That last part matters more than it sounds. A provider allowed to write into
the directory means a correction made in a console changes the source, and
within a month nobody knows where anything comes from.

The directory is running, filled with three people and two groups. The provider
is running, and knows nobody. Connect them, read only, groups included, and
then sign in with an account the provider never created.

One detail will cost you time if you let it. Both services run in containers,
and a container's `localhost` is its own. The provider will tell you the
federation is active, and import nobody, without a single error message.
