# Tutorial: three places to look, in order

This tutorial does not do the challenge. It shows you the three sources of
truth you have when an integration fails, and it shows them on **your own
broken integration**, because that is what you have in front of you.

Nothing here fixes anything. Reading first, acting after.

## 1. What the provider says on screen

Play the journey and read the message. Not the page, the message:

```bash
MDP=$(grep '^MOT_DE_PASSE=' /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)
python3 /opt/iam-lab/outils/parcours.py \
  --depart http://127.0.0.1:9080/connexion \
  --utilisateur alice --mot-de-passe "$MDP" \
  --attendre-texte "Connecté en tant que alice" \
  | jq -r '"arrivee : \(.arrivee)", "texte   : \(.texte)"'
```

Read where it stopped, then what it says. The two together tell you a lot:

- it stopped on the **provider's** address, and says something about a
  parameter: the provider refused the request, before anyone signed in;
- it stopped on the **application's** address, and the application complains:
  the provider answered, and the application did not like the answer;
- the page says `Sign in to Keycloak` instead of `Sign in to Formation IAM`:
  the application is talking to the wrong realm entirely.

That last one is worth a second look. The page title comes from the realm's
display name, and it is the fastest way to notice that an application is
knocking on the wrong door.

## 2. What the provider recorded

The screen shows one message to one user. The event log holds every attempt,
with the cause in a machine-readable field. It is enabled on this realm, which
is not the default:

```bash
KC=http://127.0.0.1:8080
U=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME=' /opt/socle-iam/.env | cut -d= -f2-)
P=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD=' /opt/socle-iam/.env | cut -d= -f2-)
ADM=$(curl -s -X POST "$KC/realms/master/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  -d "username=$U" -d "password=$P" | jq -r .access_token)

curl -s "$KC/admin/realms/formation/events?max=5" \
  -H "Authorization: Bearer $ADM" \
  | jq -r '.[] | "\(.type)\terror=\(.error // "-")\t\(.details // {} | tostring[0:80])"'
```

One line per attempt. The `error` field is the whole point: it names the cause
in a single token. Four of them matter for this lab, and they were all measured
on 2026-10-16:

| `error` | What it means |
|---|---|
| `invalid_redirect_uri` | the address the application asked to return to is not declared |
| `client_disabled` | the client exists and is switched off |
| `invalid_client_credentials` | the client expects a secret, and the application sent none |
| `not_allowed` | the flow the application asked for is closed on this client |

And a fifth case leaves **no line at all** in this realm. Think about what that
means before reading on: if the application were talking to this realm, there
would be a line. No line means it is talking to a different one.

Look at the details field too. On `invalid_redirect_uri`, it carries the URI
that was requested, which you can then compare with what the client declares:

```bash
curl -s "$KC/admin/realms/formation/clients?clientId=appli-notes" \
  -H "Authorization: Bearer $ADM" \
  | jq -r '.[0] | "declarees : \(.redirectUris)", "activee   : \(.enabled)",
                  "publique  : \(.publicClient)",
                  "flux code : \(.standardFlowEnabled)",
                  "pkce      : \(.attributes["pkce.code.challenge.method"])"'
```

Five lines, and four of the five faults are visible in them.

## 3. What the application says about itself

The application has an opinion too, and it is the only source for the fifth
fault:

```bash
curl -s http://127.0.0.1:9080/etat | jq .
```

Read `issuer` and `client_id`: that is what the application believes it is
talking to. Compare it with the realm you actually administer. And read
`derniere_erreur`, which holds the provider's refusal verbatim when the
application got far enough to be refused.

The configuration it reads is a file, and you can see it:

```bash
cat "$(grep '^CONFIGURATION_APPLI=' /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)"
```

Three keys. One of them may be wrong, and if it is, nothing in the provider's
log will tell you, because the provider never heard from this application.

## A method, in four lines

1. Play the journey. Note **where** it stopped and **what** it said.
2. Read the last events. The `error` field names the cause, or its absence
   tells you the application is elsewhere.
3. Compare what the client declares with what the application asks for.
4. Fix that one thing. Then play the journey again.

The fourth step is where this lab is actually graded. There are five ways to
make the symptom disappear without fixing the cause, and the tests check each
of them.

```bash
dsoxlab check iam-12-depanner-integration   # grade
dsoxlab hint  iam-12-depanner-integration   # one hint, at the cost of points
```
