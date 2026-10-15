"""test_functional.py : ckad-expose-service

Ces tests lisent l'état du CLUSTER, jamais les commandes tapées.

Trois affirmations. Les deux premières lisent le Deployment et le Service ;
la troisième fait dix requêtes depuis le client et compte les Pods qui ont
répondu, et c'est elle qui prouve que le Service dessert vraiment les trois
replicas : un selector qui n'en attrape qu'un passerait les deux premiers.
"""

from __future__ import annotations

import json
import time

import pytest

from conftest import lab_host, lab_target_host

NAMESPACE = "lab"
DEPLOYMENT = "web"
SERVICE = "web-svc"
CLIENT = "client"
KUBECTL = "kubectl --kubeconfig /etc/kubernetes/admin.conf"


@pytest.fixture(scope="module")
def host():
    return lab_host(lab_target_host("k8s-cp.lab"))


def _kubectl(host, args: str):
    return host.run(f"sudo {KUBECTL} {args}")


def _json(host, args: str, absent: str) -> dict:
    res = _kubectl(host, f"{args} -o json")
    assert res.rc == 0, absent
    return json.loads(res.stdout)


# ----------------------------------------------------------------------
# 1. Trois replicas prêts, labellisés app=web.
# ----------------------------------------------------------------------
def test_trois_replicas_prets(host):
    d = {}
    for _ in range(12):
        d = _json(host, f"-n {NAMESPACE} get deployment {DEPLOYMENT}", f"Aucun Deployment {DEPLOYMENT} dans {NAMESPACE}.")
        if d["status"].get("availableReplicas", 0) == 3:
            break
        time.sleep(5)
    assert d["spec"].get("replicas") == 3, f"{DEPLOYMENT} demande {d['spec'].get('replicas')} replica(s), attendu 3."
    assert d["status"].get("availableReplicas", 0) == 3, f"{d['status'].get('availableReplicas', 0)} replica(s) disponible(s) sur 3."
    assert (d["spec"]["template"]["metadata"].get("labels") or {}).get("app") == "web", (
        "Les Pods du Deployment ne portent pas app=web : c'est ce label que le Service doit sélectionner."
    )


# ----------------------------------------------------------------------
# 2. Le Service est un ClusterIP sur 80, vers 8080, et a trois endpoints.
# ----------------------------------------------------------------------
def test_le_service_expose_les_trois_pods(host):
    s = _json(host, f"-n {NAMESPACE} get service {SERVICE}", f"Aucun Service {SERVICE} dans {NAMESPACE}.")
    assert s["spec"].get("type", "ClusterIP") == "ClusterIP", f"{SERVICE} est de type {s['spec'].get('type')}, attendu ClusterIP."
    ports = s["spec"].get("ports") or []
    assert any(p.get("port") == 80 and str(p.get("targetPort")) == "8080" for p in ports), (
        f"{SERVICE} doit écouter sur 80 et viser 8080 : ports {ports}."
    )
    assert (s["spec"].get("selector") or {}).get("app") == "web", f"Le selector de {SERVICE} vaut {s['spec'].get('selector')}, attendu app=web."
    prets = []
    for _ in range(12):
        tranches = _json(host, f"-n {NAMESPACE} get endpointslices -l kubernetes.io/service-name={SERVICE}", "Lecture des EndpointSlices impossible.")
        prets = [a for t in tranches["items"] for e in t.get("endpoints") or []
                 for a in e.get("addresses") or [] if (e.get("conditions") or {}).get("ready")]
        if len(prets) == 3:
            break
        time.sleep(5)
    assert len(prets) == 3, f"{SERVICE} a {len(prets)} endpoint(s) prêt(s), attendu 3."


# ----------------------------------------------------------------------
# 3. La preuve : par son nom, et réparti entre plusieurs Pods.
# ----------------------------------------------------------------------
def test_le_service_repond_et_repartit(host):
    reponses = []
    for _ in range(10):
        res = _kubectl(host, f"-n {NAMESPACE} exec {CLIENT} -- wget -qO- -T 5 http://{SERVICE}/")
        assert res.rc == 0, f"http://{SERVICE}/ ne répond pas depuis {CLIENT} : {res.stderr.strip()[:150]}"
        reponses.append(res.stdout.strip())
    assert all(r.startswith(f"{DEPLOYMENT}-") for r in reponses), (
        f"Les réponses ne sont pas des noms de Pods de {DEPLOYMENT} : {sorted(set(reponses))}. "
        "Chaque Pod doit servir son nom d'hôte."
    )
    assert len(set(reponses)) >= 2, (
        f"Dix requêtes, un seul Pod a répondu : {set(reponses)}. Le Service ne répartit "
        "pas, ou un seul Pod est derrière lui."
    )
