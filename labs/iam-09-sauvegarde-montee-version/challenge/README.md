# Challenge: back up, upgrade, and prove it

`/opt/iam-lab/identifiants-lab.txt` names the instance's URL, its directory,
its environment file, both container names, the realm, the account password,
the starting and target versions, the exact target image, and the two
directories where your backup and your export are expected.

The instance runs **on its own ports** (`8081` and `9001`): the socle on `8080`
belongs to the other labs and must not move.

## What is expected

1. A **database backup** in `REPERTOIRE_SAUVEGARDES`, taken **before** the
   upgrade, which **restores into an empty database** with the accounts in it.
2. An **export of the realm** in `REPERTOIRE_EXPORTS`, complete enough that the
   accounts are somewhere in it.
3. The instance running in `VERSION_CIBLE`, with the image **pinned by digest**
   in the environment file, not just swapped at runtime.
4. The realm, the accounts and the clients intact.
5. The **audit trail** still in the database.
6. An account that still logs in.

## What the grading actually checks about your backup

It does not look at the file's name or size alone. It **creates a database,
restores your backup into it, counts the accounts, and drops it**. A file that
cannot be restored is not a backup, and this is the only check that tells the
difference.

It also compares your backup's timestamp to the **creation date of the target
version's container**. A backup taken afterwards fails, and it fails on
purpose: it describes a state you no longer need and cannot restore the one you
might.

## Four things measured on this machine

**`kc.sh export` run inside the running container exits 1** on « Unable to
start the management interface on 0.0.0.0:9000: Address already in use », **and
writes the files anyway**. Read the exit code and you think it failed; list the
directory and you think it worked. Run it in a throwaway container instead
(`docker compose run --rm --no-deps`) and it exits 0.

**The export writes two files, and `<realm>-realm.json` holds no accounts at
all.** `has("users")` is `false` in it. The accounts are in
`<realm>-users-0.json`. This is the trap from the scenario, and it is real.

**That accounts file carries the `credentials` with their `secretData`.** It is
a secrets file. Treat its permissions accordingly.

**The export contains no events.** The only event-related keys in it are
configuration (`eventsEnabled`, `enabledEventTypes`), not the events. The trail
lives in `event_entity` and `admin_event_entity`, in the database, and that is
why an export is not a backup.

## One thing to know about the upgrade itself

The schema migrates automatically on startup, and says so in the logs. Worth
knowing before you change the image: the 26.8 migration notes state that past
300000 rows in `OFFLINE_USER_SESSION`, the automatic migration **skips** an
index creation and logs it for you to apply by hand. A service that restarts
« with no errors » can therefore be missing an index. This instance is far too
small for that to happen here, and the habit of reading the migration notes
first is the point.

```bash
dsoxlab check iam-09-sauvegarde-montee-version   # grade
dsoxlab hint  iam-09-sauvegarde-montee-version   # one hint, at the cost of points
```
