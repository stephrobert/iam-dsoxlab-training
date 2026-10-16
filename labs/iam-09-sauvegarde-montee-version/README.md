# Tutorial: open the export and count what is in it

This tutorial does not do the challenge. It opens an export, on your own
instance, and counts what is inside, because everything this lab is about is
visible in that one file and invisible in its name. Measured on this machine on
2026-10-16.

```bash
IDS=/opt/iam-lab/identifiants-lab.txt
REALM=$(grep '^REALM=' $IDS | cut -d= -f2-)
PROD=$(grep '^REPERTOIRE_PROD=' $IDS | cut -d= -f2-)
ENVP=$(grep '^ENV_PROD=' $IDS | cut -d= -f2-)
BASE=$(grep '^CONTENEUR_BASE=' $IDS | cut -d= -f2-)
KC=$(grep '^CONTENEUR_KEYCLOAK=' $IDS | cut -d= -f2-)
URL=$(grep '^URL_PROD=' $IDS | cut -d= -f2-)
echo "instance $URL, realm $REALM, base dans $BASE"
```

## 1. The exit code says one thing, the directory says another

Export from inside the running container, which is the obvious thing to try:

```bash
sudo docker exec $KC /opt/keycloak/bin/kc.sh export \
  --dir /tmp/essai --realm "$REALM" > /tmp/essai.log 2>&1
echo "code de sortie : $?"
tail -3 /tmp/essai.log
```

It exits **1**, and the reason is nothing to do with the export: the command
starts a server to do its work, and that server cannot bind its management port
because the running Keycloak already has it.

Now look at whether it did the work anyway:

```bash
sudo docker exec $KC ls -la /tmp/essai/
```

The files are there. A script that trusts the exit code concludes the export
failed; a script that lists the directory concludes it worked. Both have read
something real, and neither has read the file.

The clean way is a throwaway container, which publishes no ports:

```bash
sudo mkdir -p /tmp/propre && sudo chown 1000:0 /tmp/propre
cd "$PROD" && sudo docker compose -f compose.yaml --env-file "$ENVP" \
  run --rm --no-deps -v /tmp/propre:/exp \
  keycloak export --dir /exp --realm "$REALM" > /tmp/propre.log 2>&1
echo "code de sortie : $?"
sudo ls -la /tmp/propre/
```

`chown 1000:0` is not decoration: the process inside that image runs as uid
1000, and a directory owned by root earns you « Error during export/import:
(Permission denied) » after ten seconds of startup.

## 2. Count what is in each file

Two files. Open both and count:

```bash
for f in /tmp/propre/*.json; do
  echo "── $(basename $f) : $(sudo stat -c %s $f) octets"
  sudo cat "$f" | jq -r '"   nb de clefs de premier niveau : \(keys | length)
   une clef users ?              : \(has("users"))
   comptes                       : \(.users | length? // 0)
   clients                       : \(.clients | length? // 0)
   flux d authentification       : \(.authenticationFlows | length? // 0)"'
done
```

The realm file has 120 top-level keys: the clients, the flows, the keys,
everything you would recognise as configuration. And `has("users")` is
**false**. Not an empty list: the key is not there. The accounts are in the
other file, the one with the boring name, the one that gets left behind when
somebody copies « the export » into a folder.

Look at the key counts, because they say something the file sizes do not. The
accounts file has exactly **two** keys, `realm` and `users`. That `realm` key
is a name, not the realm: a script that sorts the two files by asking « does
this one have a realm key » will put both of them in the configuration basket
and report that the export contains its accounts. That is a real mistake, it
was made while writing this tutorial, and the measurement above is what caught
it.

Look at what that second file carries about each account:

```bash
sudo cat /tmp/propre/"$REALM"-users-0.json | jq -r '.users[0] |
  "   compte              : \(.username)
   des credentials ?   : \(has("credentials"))
   type                : \(.credentials[0].type)
   le secret est la ?  : \((.credentials[0].secretData // "") | length > 0)"'
```

Password hashes. That file is a secrets file, and `0644` in a shared folder is
how they end up somewhere you did not intend.

## 3. What no export file contains

Ask the export about events, then ask the database:

```bash
echo "clefs de l export qui parlent d evenements :"
sudo cat /tmp/propre/"$REALM"-realm.json \
  | jq -r '[keys[] | select(test("vent"; "i"))] | "   \(.)"'

echo "et dans la base :"
for t in event_entity admin_event_entity user_entity credential; do
  n=$(sudo docker exec $BASE psql -U keycloak -d keycloak -tAc \
    "select count(*) from $t")
  printf '   %-20s %s\n' "$t" "$n"
done
```

The export's event keys are **settings**: whether events are enabled, which
types are recorded. The events themselves are rows in the database, and there
is no export flag that brings them along.

That is the whole argument of this lab in two commands. An export describes how
the provider is configured. A backup of the database contains what happened.
The question an auditor asks is always about what happened.

```bash
sudo rm -rf /tmp/propre /tmp/propre.log /tmp/essai.log
sudo docker exec $KC rm -rf /tmp/essai
```

## What this leaves you

- a command can fail and still do its work, so read the result and not the
  return code;
- « the export » is often several files, and the interesting one is rarely the
  one with the obvious name;
- configuration and history are different things, and only one of them can be
  reconstructed afterwards.

```bash
dsoxlab challenge iam-09-sauvegarde-montee-version
```
