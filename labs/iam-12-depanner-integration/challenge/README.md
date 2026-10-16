# Challenge: find the cause, and only fix that

The provider runs on `idp.lab`, realm `formation`. The application runs on port
`9080`, and its connection fails. `/opt/iam-lab/identifiants-lab.txt` holds the
test account and where the application's configuration file lives.

**The setup drew one fault at random out of five.** You do not know which, and
nothing on the machine will tell you. Four of them live in the provider, one
lives in the application.

The realm's **event log is enabled**, which is not the default. Use it.

## What is expected

The connection works again, and the final state is the correct one:

1. the client `appli-notes` exists, **enabled**, **public**, with no secret;
2. only the **authorization code flow** is open;
3. **PKCE in S256** is required, and the server refuses an exchange without it;
4. the redirect URI is **exactly** the application's, with no wildcard;
5. the application's `issuer` points at the `formation` realm.

## What is proven, and how

Six tests. The first plays the whole journey and checks the application ends up
showing the signed-in user, with a validated ID token.

The five others check that you did **not** take any of these shortcuts:

| Shortcut | What it hides | What it opens |
|---|---|---|
| a wildcard redirect URI | `invalid_redirect_uri` | an attacker receives the authorization code |
| a confidential client with its secret in the app | `unauthorized_client` | the secret is readable by anyone who installs the app |
| PKCE turned off | a whole class of errors | an intercepted code is enough to get a token |
| the password grant opened | a closed code flow | the application sees the user's password |
| the `issuer` moved elsewhere | a client that is not found | a sign-in that succeeds, with the wrong people |

The last one deserves attention: pointing the application at another realm
produces a connection that **works**. It just authenticates the wrong
population.

## Where to look, in order

```bash
# 1. What does the provider say? Play the journey and read the message.
python3 /opt/iam-lab/outils/parcours.py \
  --depart http://127.0.0.1:9080/connexion \
  --utilisateur alice --mot-de-passe "$(grep '^MOT_DE_PASSE=' \
    /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)" \
  --attendre-texte "Connecté" | jq -r '.texte, .arrivee'
```

Then the event log, which names the cause in one word. Then the application's
own state at `http://127.0.0.1:9080/etat`, which says what it read and what it
refused.

## One thing to resist

When you find the cause, fix **that**. The temptation is to fix it and, while
you are in the screen, to loosen two other things that look suspicious. Each of
those is a test you will fail, and in production each one is an incident
waiting.

```bash
dsoxlab check iam-12-depanner-integration   # grade
dsoxlab hint  iam-12-depanner-integration   # one hint, at the cost of points
```
