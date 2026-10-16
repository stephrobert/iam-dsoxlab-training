# Monday morning, and nothing is wired

The company has a directory. It has been there for years, it holds the three
people who will use what you build today, and it works. It is the only thing
that works.

There is no identity provider. There is an application that shows notes, and an
API that serves them, and both were written by somebody who left. The
application has no login page. The API answers anybody who asks, which is how
the notes ended up in a support ticket last month, pasted by somebody who was
not supposed to see them.

You have the machine, the directory, and until the end of the morning.

What is expected is not a demonstration. It is a provider that is still there
after the machine reboots, a directory whose accounts and groups are usable
through it, an application that sends people to the provider and shows their
name when they come back, and an API that refuses what it should refuse.

That last one is the part people get wrong, and they get it wrong in a specific
way: they make the API check that the token is valid. A token from this
provider, for this person, issued for an entirely different application, is
valid. If that is enough for your API, then every application in the realm can
read the notes, and you have built the ticket from last month again with more
steps.

There are no hints in this exercise. The tests read the state of the system, so
how you get there is your business: console, API, script, it makes no
difference. What matters is what is true at the end.

The specification is in `/opt/iam-lab/identifiants-lab.txt`. It names
everything the tests look for, because an exam that hid the names would measure
guesswork.
