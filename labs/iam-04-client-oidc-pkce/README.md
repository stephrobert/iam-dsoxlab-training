# Tutorial: three mechanisms to see at work

This tutorial does not do the challenge. It shows you the three mechanisms the
challenge needs, at work, on throwaway examples. Nothing here touches the
`formation` realm or the `appli-notes` client, and that is deliberate: you will
have to carry the ideas over yourself.

Work in a temporary directory:

```bash
cd "$(mktemp -d)"
```

## 1. PKCE, with no server involved

PKCE is often described as a protocol feature. It is three lines of
arithmetic, and seeing them removes the mystery.

The application invents a random string, the **verifier**. It hashes it and
sends only the hash, the **challenge**, when it asks for a code. Later, when it
exchanges the code for a token, it presents the verifier. The server hashes it
again and compares.

```bash
# The verifier: random, kept by the application, never sent at this stage.
# 48 bytes, not 32: stripping the characters base64url forbids shortens the
# string, and RFC 7636 requires at least 43. Measured over 200 draws,
# `-base64 32` fell short 144 times, down to 37 characters.
verifieur=$(openssl rand -base64 48 | tr -d '=+/' | cut -c1-43)
echo "verifier : $verifieur  (${#verifieur} characters)"

# The challenge: its SHA-256, in base64url without padding
defi=$(printf '%s' "$verifieur" | openssl dgst -binary -sha256 \
  | openssl base64 | tr '+/' '-_' | tr -d '=')
echo "challenge: $defi"
```

Now see why it works. Compute the challenge again from the same verifier: you
get the same string. Compute it from a different one: nothing in common.

```bash
printf '%s' "$verifieur" | openssl dgst -binary -sha256 \
  | openssl base64 | tr '+/' '-_' | tr -d '='
printf '%s' "autre-chaine" | openssl dgst -binary -sha256 \
  | openssl base64 | tr '+/' '-_' | tr -d '='
```

Someone who steals the authorization code has the code, and not the verifier.
Without it, the exchange fails. That is the whole protection, and it only works
if the server **requires** the verifier instead of accepting an exchange
without it.

The other method, `plain`, sends the verifier itself as the challenge. Whoever
can read one can read the other, and the protection disappears. There is no
reason to pick it.

## 2. What a realm says about itself

An OIDC provider publishes its own description at a fixed address. You never
have to guess an endpoint, and you never have to guess the issuer.

```bash
curl -s http://127.0.0.1:8080/realms/master/.well-known/openid-configuration \
  | jq '{issuer, authorization_endpoint, token_endpoint,
         code_challenge_methods_supported, grant_types_supported}'
```

Three things to notice.

The `issuer` is a **string**, and applications compare it character for
character. It is not "the server's address": it carries the realm. Read it,
copy it, never retype it.

`code_challenge_methods_supported` lists `plain` and `S256`. The server
*supports* both. Which one a given client *requires* is a client setting, and
the discovery document says nothing about it.

Now ask the same question of a different realm, and compare the `issuer`:

```bash
curl -s http://127.0.0.1:8080/realms/formation/.well-known/openid-configuration \
  | jq -r .issuer
```

Two realms, two issuers, the same server. An application that only checked the
signature would accept tokens from both, because both are signed by the same
installation with perfectly valid keys. It is `iss` that separates them.

## 3. Two tokens, read from the inside

A token is not opaque. Its payload is base64url, and anyone holding it can read
it. Doing it once changes how you think about what belongs in one, and it shows
something most explanations get wrong.

Ask the `master` realm for tokens, with its administration client, which has
the password grant open:

```bash
U=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME:' /opt/socle-iam/secrets.yml | cut -d'"' -f2)
P=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD:' /opt/socle-iam/secrets.yml | cut -d'"' -f2)
REPONSE=$(curl -s -X POST \
  http://127.0.0.1:8080/realms/master/protocol/openid-connect/token \
  -d grant_type=password -d client_id=admin-cli -d scope=openid \
  -d "username=$U" -d "password=$P")
echo "$REPONSE" | jq -r 'keys | join(", ")'
```

Two tokens come back, and they are not interchangeable. Read both payloads.
The helper below completes the base64url padding, which `base64 -d` needs:

```bash
charge() {
  local c=$(echo "$1" | cut -d. -f2)
  local pad=$(( (4 - ${#c} % 4) % 4 ))
  [ "$pad" -gt 0 ] && c="$c$(printf '=%.0s' $(seq 1 "$pad"))"
  echo "$c" | tr '_-' '/+' | base64 -d
}

echo "access token :"
charge "$(echo "$REPONSE" | jq -r .access_token)" | jq -r 'keys | join(", ")'
echo "ID token :"
charge "$(echo "$REPONSE" | jq -r .id_token)" | jq -r 'keys | join(", ")'
```

Measured on Keycloak 26.8.1, the access token carries only `azp, exp, iat,
iss, jti, scope, sid, typ`. **No `aud`, and no `sub`.** The ID token carries
`aud`, `sub`, `preferred_username` and `typ: ID`.

That is worth stopping on, because it contradicts the usual summary. An access
token says *what may be done*, and Keycloak can issue it in a lightweight form
that holds almost nothing. An ID token says *who signed in*, and it is the one
an application validates to know its user. Asking an access token who the user
is may get you nothing at all.

```bash
charge "$(echo "$REPONSE" | jq -r .id_token)" | jq '{iss, aud, azp, exp, typ}'
```

Read `iss`: it names the realm, not just the host. Read `aud`: it names the
client this token is for. Read `exp`: a timestamp, after which it is worth
nothing.

Then look at what you just did: you read a token's contents with no key at all.
The signature protects it from **modification**, not from reading. Nothing
secret belongs in a token.

And note the grant you used: `grant_type=password`, with the username and
password passed straight through. It is convenient for a test, and it is
precisely what the challenge asks you to close on your own client.

## What the challenge asks now

You have seen that PKCE is a hash to be checked, that a realm publishes its own
issuer, and that an access token and an ID token do not say the same things.

The challenge asks you to assemble this for real: give the application an
identity with the provider, require the proof, declare the exact return
address, close what should be closed, and point the application at the right
realm.

```bash
dsoxlab check iam-04-client-oidc-pkce   # grade
dsoxlab hint  iam-04-client-oidc-pkce   # one hint, at the cost of points
```
