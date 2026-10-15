#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le Deployment : chaque Pod sert son nom d'hôte, qui est le nom du Pod.
cat <<'YAML' | $K apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: web
          image: busybox:1.36
          command: ["sh", "-c", "mkdir -p /www && hostname > /www/index.html && exec httpd -f -p 8080 -h /www"]
          ports:
            - containerPort: 8080
YAML
$K -n lab rollout status deployment/web --timeout=180s

# 2. Le Service, en une commande.
$K -n lab expose deployment web --name=web-svc --port=80 --target-port=8080

# 3. La preuve : le nom répond, et plusieurs Pods se partagent les requêtes.
sleep 3
for essai in $(seq 1 10); do
  $K -n lab exec client -- wget -qO- -T 5 http://web-svc/
done | sort | uniq -c
echo "web-svc répartit les requêtes entre les Pods de web."
