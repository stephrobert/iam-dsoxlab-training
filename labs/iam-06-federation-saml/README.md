# Tutorial: three mechanisms to see at work

This tutorial does not do the challenge. It shows you the three mechanisms SAML
rests on, at work, by reading what the two realms already publish about
themselves. Nothing here declares the client or the identity provider.

Read the lab's details first:

```bash
cat /opt/iam-lab/identifiants-lab.txt
```

## 1. Metadata: nobody guesses anything

An OIDC provider publishes a JSON document. A SAML one publishes XML, at a
fixed address, and it contains everything the other side needs:

```bash
KC=http://127.0.0.1:8080
curl -s "$KC/realms/formation/protocol/saml/descriptor" \
  | head -c 700; echo
```

Three things are in there, and each one answers a field you will have to fill
in.

The **entity identifier**, which is who the issuer claims to be:

```bash
curl -s "$KC/realms/formation/protocol/saml/descriptor" \
  | grep -oE 'entityID="[^"]+"'
```

The **sign-on address**, where the browser is sent:

```bash
curl -s "$KC/realms/formation/protocol/saml/descriptor" \
  | grep -oE 'SingleSignOnService[^>]*Location="[^"]+"' | head -2
```

And the **certificate** that signs what the issuer sends:

```bash
CERT=$(curl -s "$KC/realms/formation/protocol/saml/descriptor" \
  | grep -oE '<ds:X509Certificate>[^<]+' | head -1 | sed 's/.*>//')
echo "longueur : ${#CERT}"
echo "$CERT" | head -c 60; echo "..."
```

Look at what that certificate actually is, by decoding it:

```bash
printf -- '-----BEGIN CERTIFICATE-----\n%s\n-----END CERTIFICATE-----\n' "$CERT" \
  | openssl x509 -noout -subject -issuer -dates
```

A self-signed certificate belonging to the realm. The consumer will trust
assertions **because** they carry a signature it can check against this. Copy
it from anywhere else and nothing will verify.

## 2. The address that derives from a name

The consumer has an address where it receives assertions, and that address is
not free. It is built from the realm and from the **alias** of the identity
provider:

```bash
grep -E '^(ENTITE|ACS|ALIAS)' /opt/iam-lab/identifiants-lab.txt
```

Read it carefully: `.../realms/partenaire-sp/broker/saml-formation/endpoint`.
The `saml-formation` in the middle is the alias. Name the identity provider
something else and that address changes, the issuer's client declares the wrong
one, and the assertion is sent where nobody is listening.

That address does not exist yet, because the identity provider does not exist
yet:

```bash
curl -s -o /dev/null -w 'ACS : HTTP %{http_code}\n' \
  "$KC/realms/partenaire-sp/broker/saml-formation/endpoint"
```

And the consumer's own metadata, which an issuer would normally be given, has
nothing to publish either:

```bash
curl -s -o /dev/null -w 'metadonnees du consommateur : HTTP %{http_code}\n' \
  "$KC/realms/partenaire-sp/broker/saml-formation/endpoint/descriptor"
```

That is the chicken and egg of SAML, and it is why the alias is imposed by this
challenge: you need to know the address before the thing that serves it exists.

## 3. How an assertion crosses a browser

OIDC moves a browser with HTTP redirects. SAML does not. It hands the browser a
form containing the assertion and has JavaScript submit it.

You can see the difference without configuring anything, on the OIDC side that
is already in place. Watch what the witness application does:

```bash
curl -s -o /dev/null -w 'connexion : HTTP %{http_code}, vers %{redirect_url}\n' \
  http://127.0.0.1:9080/connexion
```

A `302`, and a destination in the header. That is a redirect: one line, visible
in any trace.

Now look at the tool the tests use, and at what it had to learn to follow SAML:

```bash
grep -A6 'auto-soumis' /opt/iam-lab/outils/parcours.py | head -20
```

It looks for a form whose method is `post`, which carries hidden fields, and
whose page calls `.submit()`. Then it posts it itself. Without that, a SAML
journey stops at the first of these forms, and the trace shows nothing wrong:
the last response was a perfectly ordinary `200`.

This is worth understanding before you debug anything, because it changes where
you look. A SAML integration does not fail in a redirect chain. It fails in the
content of a form, or in the signature of what that form carries.

When you have built both sides, you will see the full journey. It is eight
steps, with two of those self-submitting forms, and the tests print them when
they fail.

## What the challenge asks now

You have seen that each side publishes everything the other needs, that the
consumer's address derives from an alias you choose, and that the assertion
travels inside forms rather than redirects.

The challenge asks for the client that signs, the identity provider that
verifies, the attributes that must cross, and the group that must follow.

```bash
dsoxlab check iam-06-federation-saml   # grade
dsoxlab hint  iam-06-federation-saml   # one hint, at the cost of points
```
