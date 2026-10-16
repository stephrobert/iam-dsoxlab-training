# Somebody changed something

The realm works. It took three weeks of console clicks to get there, spread
over four months, by five people, and it works. Nobody can say what it
contains. There is a wiki page listing the clients, written in March, and two
of those clients no longer exist.

Last Tuesday something stopped working for one application, and the
investigation found that a token lifetime had been changed from ten minutes to
thirty. The change is in the admin event log, with a date and an account name.
The account belongs to somebody who no longer works here, and the log says what
was changed, not why.

That is the real cost of a configuration that lives only in the server: not
that it drifts, but that nothing can distinguish a deliberate change from a
mistake. Both appear the same way, both are already in production, and the only
record of intent is somebody's memory.

So you are going to write it down instead. Not in a wiki page, which drifts
without telling anybody, but in files that a tool reads and enforces, so that
the question « what should this realm contain » has a single answer, and the
question « has anybody changed it » can be answered by a command rather than an
investigation.

You will describe a small realm: two roles, a group, a public client and a
confidential one. Then you will apply it, change something by hand the way
Tuesday's change was made, and watch the files take the realm back.

Two warnings, both about what « versioned » implies.

A confidential client has a secret. Not writing that secret in your files is
the obvious move, and it is not sufficient: the tool keeps a record of
everything it manages, and that record is a file on disk with default
permissions. Go and look at it before you decide you are done.

And the tool authenticates somewhere in order to do its work. That somewhere is
a realm, and it is not the realm you are describing. Confuse the two and you
will apply your specification to the administrative realm, or to the one the
other labs depend on, and the grading checks both.
