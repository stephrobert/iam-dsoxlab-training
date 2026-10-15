#!/usr/bin/env bash
# Pose la situation : un namespace avec un client, et ni Deployment ni
# Service.
#
# Rejouable : le namespace est attendu s'il se termine, et les objets d'un
# passage précédent sont retirés.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace lab -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/lab --timeout=180s
fi
kubectl get namespace lab >/dev/null 2>&1 || kubectl create namespace lab

kubectl -n lab delete service web-svc --ignore-not-found
kubectl -n lab delete deployment web --ignore-not-found --wait=true

cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: lab
spec:
  containers:
    - name: client
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
EOF
kubectl -n lab wait --for=condition=Ready pod/client --timeout=180s

echo "Situation posée : client attend web-svc."
