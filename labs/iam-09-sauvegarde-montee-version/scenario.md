# The backup nobody has ever restored

The upgrade is scheduled for Thursday evening. The provider is two minor
versions behind, one of them carries a fix somebody needs, and the change
request says, under the heading « rollback plan », the words « restore from
backup ».

There is a backup. It runs every night, it has never failed, and nobody has
ever restored it. Those two facts are usually stated as one reassuring
sentence, and they are not the same fact at all. A backup that has never been
restored is a file whose contents nobody has checked, produced by a command
whose exit code nobody reads, about a database whose shape has changed twice
since the script was written.

There is also an export. Somebody exported the realm last month, before a
configuration change, and kept the file. It is sitting in a shared folder
called `backups`, and it is four hundred kilobytes of JSON that looks
complete, with the realm, the clients, the authentication flows and the keys
all in it.

It is not a backup, and the way it is not a backup is worth your afternoon.
The file somebody kept is one of two that the export command produces, and it
is the one that contains no accounts. Restore from it on Friday morning and you
will have a realm with every setting in place, every client configured, and
nobody able to log in.

What it also does not contain, regardless of which file you keep, is the record
of who logged in and when. That record lives in the database, in tables the
export does not look at. Lose it in an upgrade and the question « who had
access in March » stops having an answer, permanently.

So: an instance is running, one version behind, with accounts, clients and a
few days of audit trail. Back it up properly, upgrade it, and then prove that
nothing was lost, which means proving it about the trail as well as the
accounts.

The order matters, and it is the only part of this lab that cannot be fixed
afterwards.
