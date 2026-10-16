# Everything, on one machine, before the end of the day

The audit is in three weeks. The auditor sent their list of questions early,
which is a courtesy, and the list is short enough to read in a minute and long
enough to explain why nobody has slept well since.

Who can log in. Where their accounts live. What happens when somebody leaves.
Whether anybody has a second factor. Whether you can prove any of it.

Right now the honest answers are: nobody knows, in four places, nothing,
no, and no.

You have a machine, a directory with three people in it, an application that
has no login page, and an API that answers anybody who asks. You have until the
end of the day.

What the auditor will actually check is not your configuration. It is whether
the state of the system matches what you told them. So that is what this exam
checks too: sixteen readings of the system, and not one of them cares how you
got there.

Four of those readings are worth thinking about before you start.

**The provider has to survive a restart.** Not because restarts are frequent,
but because a provider that loses its realm on reboot has no realm, it has a
demonstration.

**The second factor goes to the sensitive group, and only to it.** Imposed on
everybody, it locks out the administrator, and the usual remedy at that point
is to disable the whole thing on Monday morning. Imposed on nobody, which is
the more common outcome, it passes every visual inspection: the step is there,
it is required, and the people who have no second factor walk straight through.

**The departure has to be finished.** Three gestures, and two of them answer
« done » without having done anything. One of them is refused by the provider
itself, politely, in a way you have to go looking for.

**The backup has to restore.** Not exist: restore. This exam creates a
database, puts your backup into it, and counts what came back. An export of the
realm will not pass, and it will not pass for a reason the auditor cares about:
it contains no record of who logged in.

The specification is in `/opt/iam-lab/identifiants-lab.txt`. It names the three
accounts and the role each one plays in this exam, and it is worth reading that
part carefully: one of the three must not be in the sensitive group, and the
specification tells you which.

There are no hints.
