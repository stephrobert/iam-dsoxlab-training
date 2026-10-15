# Expose a Deployment through a ClusterIP Service

## The situation

In the **`lab`** namespace, the team wants a web server in **three replicas**,
reachable by the other applications of the cluster under a stable name,
**`web-svc`**, whichever Pod answers. To check the spread, each Pod must answer
with **its own name**.

A Pod named **`client`** is there to query the Service.

## What you must achieve

1. A Deployment **`web`** in `lab`, three replicas, image `busybox:1.36`,
   where each Pod serves its hostname over HTTP on port **8080**. Its Pods
   carry the label `app=web`.

2. A Service **`web-svc`** of type ClusterIP, port **80**, pointing at port
   8080 of the `app=web` Pods.

3. From `client`, `http://web-svc/` answers, and over about ten requests, **at
   least two different Pods** answer.

## Useful bearings

A server that answers with its hostname fits in one busybox command:
`hostname` into a file, then `httpd -f` on that directory. Inside a Pod, the
hostname is the Pod name.

`kubectl expose deployment` creates the Service in a single command, if you
tell it the port and the target port.

## How you will know it works

The tests read the Deployment and the Service, then make ten requests from
`client` and count the Pods that answered.

```bash
dsoxlab check ckad-expose-service
```
