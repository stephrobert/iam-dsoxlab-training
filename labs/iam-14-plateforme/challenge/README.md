# The cluster has its own list of who you are

## The situation

Access to the cluster works by certificate. Each person who needs `kubectl` has
been handed a key and a certificate, generated once, by whoever was on duty
that day. The files were sent over chat. They do not expire in any useful
sense, and nobody knows who holds a copy.

When somebody leaves, their directory account is disabled within the hour. The
certificate keeps working. There is no list of issued certificates, and there
is no way to revoke one: the cluster has no revocation to check. The only
honest fix is to rotate the certificate authority, which invalidates everyone
at once, which is why it has never been done.

The cluster, in other words, has its own list of who people are, and that list
drifts away from the directory from the moment it is written.

You are going to replace it. The cluster can be told to trust the identity
provider instead: a person runs `kubectl`, gets a token from the provider, and
the cluster reads it. Leaving the company then closes the cluster too, because
there is only one place where accounts live.

Two things have to be true for that to be worth doing.

The rights must follow the **group**, not the person. If you bind rights to
usernames, you have rebuilt the drift somewhere else, in a file this time. And
the group must be bound to something **bounded**: there is a role that grants
the entire cluster, it would make the lab pass, and it would hand the machine
to whoever can get themselves added to a group in the directory, which is not
a decision the cluster gets to review.

While you are at it, the platform's dashboard needs the same treatment, for the
same reason: it has its own local accounts, and three of them belong to people
who left.

One warning about this lab, which is not about identity at all. A cluster's API
server refuses to trust a provider over plain HTTP, and it refuses by not
starting, with the reason in a log you have to go and read. The setup has
already placed a TLS access in front of the provider so that you can do the
work. Keep in mind that the provider now answers on two doors, and that it does
not say the same thing about itself on each one.

## A cluster and a tool that trust the provider

`/opt/iam-lab/identifiants-lab.txt` names everything the tests look for: the
cluster name, the namespace, the two groups and their accounts, the client ids,
the audience, both issuers, the CA path, where the authentication
configuration is expected, and the tool's environment file.

The setup has installed `k3d` and `kubectl`, pulled the cluster image, put a
**TLS access in front of the provider**, created two groups with one account
each, and started the tool **without** any knowledge of the provider. There is
no cluster yet. Creating it is yours.

### What is expected

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

### What costs an afternoon, measured on this machine

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

### Two failure cases the grading catches

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
