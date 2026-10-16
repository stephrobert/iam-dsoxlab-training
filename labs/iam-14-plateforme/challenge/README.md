# Challenge: a cluster and a tool that trust the provider

`/opt/iam-lab/identifiants-lab.txt` names everything the tests look for: the
cluster name, the namespace, the two groups and their accounts, the client ids,
the audience, both issuers, the CA path, where the authentication
configuration is expected, and the tool's environment file.

The setup has installed `k3d` and `kubectl`, pulled the cluster image, put a
**TLS access in front of the provider**, created two groups with one account
each, and started the tool **without** any knowledge of the provider. There is
no cluster yet. Creating it is yours.

## What is expected

1. A cluster named as `CLUSTER_ATTENDU` says, whose API server reads an
   **authentication configuration**.
2. That configuration names the **TLS issuer**, requires the audience, and
   carries the provider's CA.
3. A client `kubernetes`: public, PKCE `S256`, with an **audience mapper** and
   a **group mapper**.
4. A token taken from the TLS door authenticates the account **with its
   group**; a token taken from the HTTP door is **refused**.
5. `devops` writes in the `applications` namespace and **nowhere else**;
   `lecteurs` reads everywhere and writes nothing; **no group is bound to
   `cluster-admin`**.
6. The tool lets the account in **through the provider**, all the way to a
   session.

## What costs an afternoon, measured on this machine

**In Kubernetes 1.37 the `--oidc-*` flags are gone.** Only the structured
configuration remains, `apiVersion: apiserver.config.k8s.io/v1beta1`, passed
with `--authentication-config`. Every tutorial written before 1.29 shows flags
that no longer exist.

**It refuses an issuer over http**, and it refuses by **not starting**:

```text
Error: invalid authentication configuration: jwt[0].issuer.url:
Invalid value: "http://...": URL scheme must be https
```

What you see instead is `k3d` giving up after a timeout, saying the node failed
to get ready. The reason is in `docker logs k3d-<cluster>-server-0`, and `k3d`
deletes that container while rolling back, so pass `--no-rollback` when you
want to read it.

**The provider answers on two doors and does not describe itself the same way
on each.** It computes its issuer from the request. Ask
`.well-known/openid-configuration` on each door and compare, before you write
anything into the cluster's configuration.

**The API server must resolve the issuer's name from inside its container.**
`k3d` has an option for that, and without it you get a correct configuration
that cannot fetch the provider's keys.

**`kubectl --token` is ignored when the current kubeconfig holds a client
certificate.** `auth whoami` then answers `system:admin` with `system:masters`,
and you conclude your OIDC works when you have just measured your own admin
certificate. Use an empty kubeconfig to test a token. This one is worth
remembering well beyond this lab.

## Two failure cases the grading catches

**A group bound to `cluster-admin`.** It works, it is one command, and it gives
the machine away to whoever can join a group in a directory you do not
administer.

**A token without the groups claim.** The account authenticates, carries only
`system:authenticated`, and is refused although the RBAC binding exists. It
looks exactly like broken RBAC and it is not: ask for the claim on the client.

```bash
dsoxlab check iam-14-plateforme   # grade
dsoxlab hint  iam-14-plateforme   # one hint, at the cost of points
```
