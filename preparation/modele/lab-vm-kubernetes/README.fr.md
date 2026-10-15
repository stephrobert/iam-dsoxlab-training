# Exposer un Deployment par un Service ClusterIP

Lab **CKAD**, domaine *Services and Networking* (20 % de l'épreuve),
compétence « Provide and troubleshoot access to applications via services ».

Le lab hérité lisait six specs sans jamais faire de requête. Ici chaque Pod
répond son nom, et dix requêtes depuis un client doivent atteindre au moins
deux Pods.

| | |
|---|---|
| Cible | `k8s-cp.lab`, control plane du cluster kubeadm vanilla |
| Durée | environ 10 minutes |
| Leçon jumelée | [Les Services](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/) |

```bash
dsoxlab run   ckad-expose-service
dsoxlab check ckad-expose-service
```

Transposé de K8sExamLab le 2026-09-15, puis validé par
`scripts/valider-labs.py` : 0 avant le travail, 100 après la solution du
formateur, rejouable et sans trace.
