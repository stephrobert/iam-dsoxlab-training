# Expose a Deployment through a ClusterIP Service

**CKAD** lab, *Services and Networking* domain (20 % of the exam), competency
"Provide and troubleshoot access to applications via services".

The inherited lab read six specs without ever making a request. Here each Pod
answers with its own name, and ten requests from a client must reach at least
two Pods.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 10 minutes |
| Companion lesson | [Services](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/) |

```bash
dsoxlab run   ckad-expose-service
dsoxlab check ckad-expose-service
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
