# Tutorial: two doors, and a flag that is quietly ignored

This tutorial does not do the challenge. It makes you see three things, on
throwaway clusters you delete right after, that would each cost you an
afternoon inside the challenge. Measured on this machine on 2026-10-16.

```bash
IDS=/opt/iam-lab/identifiants-lab.txt
REALM=$(grep '^REALM=' $IDS | cut -d= -f2-)
IP=$(grep '^IP_MACHINE=' $IDS | cut -d= -f2-)
CA=$(grep '^CA_IDP=' $IDS | cut -d= -f2-)
echo "machine $IP, realm $REALM, certificat du fournisseur $CA"
```

## 1. The provider does not describe itself the same way on each door

The setup put a TLS access in front of the provider. Both doors are open. Ask
each one who it says it is:

```bash
echo "par la porte HTTP :"
curl -s "http://127.0.0.1:8080/realms/$REALM/.well-known/openid-configuration" \
  | jq -r '"   iss  = \(.issuer)\n   jwks = \(.jwks_uri)"'

echo "par la porte TLS :"
curl -s --cacert "$CA" --resolve "idp.lab:8443:127.0.0.1" \
  "https://idp.lab:8443/realms/$REALM/.well-known/openid-configuration" \
  | jq -r '"   iss  = \(.issuer)\n   jwks = \(.jwks_uri)"'
```

Same realm, same accounts, same passwords, two different issuers. The provider
computes its issuer from the request it received, so the door you knock on ends
up written inside every token it hands you.

A cluster compares the `iss` of a token against the one issuer it was
configured with. One of these two doors is therefore the right one, and the
other produces tokens that are perfectly valid and systematically refused.
Nothing in the token looks wrong.

## 2. A flag that is accepted and ignored

Make a bare cluster, with no identity configuration at all:

```bash
k3d cluster create essai-tuto --servers 1 --agents 0 --api-port 6551
```

Now hand it a token that does not exist, and ask who it thinks you are:

```bash
kubectl --server https://127.0.0.1:6551 --insecure-skip-tls-verify \
  --token "ceci-n-est-pas-un-jeton" auth whoami
```

Read that answer carefully. It says `system:admin`, with the group
`system:masters`, and it tells you the credential was an **X509 certificate**.
You passed a token. It was ignored, because the current kubeconfig holds a
client certificate and that wins.

This is how people conclude that their OIDC integration works. They configure
it, they test it with `--token`, they get an answer, and the answer came from
their own administrative certificate. The test passes before the work is done.

The fix is to leave the token as the only credential available:

```bash
kubectl --kubeconfig /dev/null --server https://127.0.0.1:6551 \
  --insecure-skip-tls-verify --token "ceci-n-est-pas-un-jeton" auth whoami
```

Now it fails, which is the correct answer to a token nobody issued. Keep
`--kubeconfig /dev/null` for anything you measure with a token, in this lab and
after it.

```bash
k3d cluster delete essai-tuto
```

## 3. The API server refuses http by not starting

Write an authentication configuration that points at the HTTP door, which is
the natural thing to write since that is the door every other lab uses:

```bash
sudo mkdir -p /etc/k3d-tuto
sudo tee /etc/k3d-tuto/auth.yaml > /dev/null <<CONF
apiVersion: apiserver.config.k8s.io/v1beta1
kind: AuthenticationConfiguration
jwt:
  - issuer:
      url: http://$IP:8080/realms/$REALM
      audiences:
        - kubernetes
    claimMappings:
      username:
        claim: preferred_username
        prefix: ""
CONF
echo "config écrite"
```

Then try to start a cluster that reads it. This takes a minute, and the minute
is the lesson:

```bash
k3d cluster create essai-http --servers 1 --agents 0 --api-port 6552 \
  --no-rollback \
  --volume /etc/k3d-tuto:/etc/k3d-tuto@server:0 \
  --k3s-arg "--kube-apiserver-arg=authentication-config=/etc/k3d-tuto/auth.yaml@server:0" \
  --timeout 60s
```

What you get is a timeout: the node never became ready. Nothing says why. The
reason is inside the container, and `--no-rollback` is why the container still
exists for you to ask:

```bash
docker logs k3d-essai-http-server-0 2>&1 \
  | grep -iE 'invalid authentication|URL scheme' | head -3
```

```text
Error: invalid authentication configuration: jwt[0].issuer.url:
Invalid value: "http://...": URL scheme must be https
```

That is a single sentence, and it is the whole explanation. Without
`--no-rollback`, `k3d` deletes the container as it cleans up after itself, and
you are left with a timeout and no reason, which is where people start
suspecting memory, the image, or the network.

```bash
k3d cluster delete essai-http
sudo rm -f /etc/k3d-tuto/auth.yaml && sudo rmdir /etc/k3d-tuto
```

## What this leaves you

- a provider can answer on several doors, and the door is recorded in the
  token: check what it says about itself before you trust what you assumed;
- a credential you pass is not necessarily the credential that was used, and
  the safe way to measure one is to make it the only one available;
- a component that refuses by not starting puts its reason in its own logs, so
  keep the evidence alive long enough to read it.

```bash
dsoxlab challenge iam-14-plateforme
```
