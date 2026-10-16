# Tutorial: three mechanisms to see at work

This tutorial does not do the challenge. It shows you the three mechanisms the
challenge needs, at work, on throwaway examples. The names used here are not
the challenge's, and that is deliberate: you will have to carry them over.

Work in a temporary directory, so you leave nothing behind:

```bash
cd "$(mktemp -d)"
```

## 1. A service that waits for another to be ready

Two containers started together do not start in the right order. A service
talking to a database must wait for the database to **accept connections**,
which happens well after its container has started.

Compose can express that, but only if the dependency carries a **condition**
and the database declares a **health probe**. Let us see both on an example
unrelated to the challenge.

```yaml
# compose.yaml, in your temporary directory
name: demo-horloge

services:
  horloge-db:
    image: postgres:18.6
    environment:
      POSTGRES_PASSWORD: demo
      POSTGRES_DB: horloge
      POSTGRES_USER: horloge
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U horloge -d horloge"]
      interval: 3s
      retries: 10

  horloge:
    image: alpine:3.22
    command: ["sh", "-c", "echo 'the database was ready at' $(date -Iseconds); sleep 5"]
    depends_on:
      horloge-db:
        condition: service_healthy
```

Run it, and watch the order in which things happen:

```bash
docker compose up
```

`horloge` only prints its line once the database reports healthy. Now drop the
condition, replacing the `depends_on` block with the short form, and run again:

```yaml
    depends_on:
      - horloge-db
```

```bash
docker compose down -v && docker compose up
```

This time `horloge` speaks straight away: Compose only waited for the
database's container to **start**, not for it to be ready. The difference is
invisible on an `echo`, and not invisible at all for a service that opens a
connection and gives up when it is refused.

Clean up before moving on:

```bash
docker compose down -v
```

## 2. Where a server says it is well

A production service exposes its state somewhere other than its application
port. Mixing them would be a mistake: health and metrics concern the operator,
not the visitor, and publishing them in the same place would make them
available to everyone.

Try the principle on any service:

```bash
docker run -d --name demo-sonde -p 18080:80 nginx:1.29-alpine
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18080/
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18080/etat
docker rm -f demo-sonde
```

The first call returns `200`, the second `404`: this server has no state
endpoint, and nothing says it is well other than the fact that it answers.

Keycloak does have one, and it lives on a **separate port** from the
application's. That port always exists, but the state endpoint is only served
if the configuration allows it. The site's installation page names the variable
that enables it, and the port concerned.

## 3. Creating an account through the API, without the screen

The web administration console is pleasant and cannot be scripted. Everything
it does, the administration API does too, and that is the path operations take.

The principle has two steps: get a token with an account that has the right,
then use it. Let us see it against a public demonstration service, so nothing
of yours is touched:

```bash
# A token, with an account and a password, against a known endpoint
curl -s -X POST https://httpbin.org/post \
  -d grant_type=password -d client_id=demo-cli \
  -d username=jean-meteo -d password=bulletin \
  | jq '.form'
```

The reply echoes what you sent: the shape of the request is there, and that is
all we care about. Against a real server, this request returns an
`access_token`, which you then present in a header:

```bash
curl -s https://httpbin.org/headers \
  -H "Authorization: Bearer a-demonstration-token" \
  | jq '.headers.Authorization'
```

Two things to remember for the challenge, which often come as a surprise.

A **server** administrator does not live in the same realm as application
accounts. An account created in a realm administers that realm, not the server.

And the bootstrap account is not an account like the others: its password is
passed to the container through an environment variable, so it is readable with
`docker inspect`. That is why it is called temporary.

## What the challenge asks now

You have seen a dependency conditioned by a probe, a state endpoint on a
separate port, and the creation of an account through an API. The challenge
asks you to assemble them for real, on Keycloak, and to remove behind you what
must not remain.

```bash
dsoxlab check iam-02-keycloak-installer   # grade
dsoxlab hint  iam-02-keycloak-installer   # one hint, at the cost of points
```
