# Authentication, and nobody to run it

The team shipped three internal applications in six months. Each has its own
login screen, its own user table, and its own way of losing passwords. When
someone leaves, you have to remember to remove them from three places, and
nobody can say whether that was done.

The decision is made: one identity provider, a single one, in front of all
three.

You inherit the machine meant to host it. It is bare, and it is up to you to
run Keycloak there as a service you leave in production, not as a demo that
evaporates on first restart.

Two things matter more than seeing the login screen appear.

The first is **persistence**. Keycloak can start on its own, with no database,
keeping everything in memory or in a file of its own. That is convenient for
trying things out, and a trap in production: the day the container restarts,
the accounts, the declared applications and the sessions are gone. So you will
back Keycloak with a real database.

The second is the **administration account**. On first startup, Keycloak asks
for a temporary account passed through an environment variable, visible to
anyone who can inspect the container. That account exists to create the real
one, and must not outlive it.
