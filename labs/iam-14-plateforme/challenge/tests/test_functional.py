"""Un cluster qui fait confiance à l'IdP, des droits qui suivent le groupe, et
un outil qui laisse entrer.

SEPT FAITS MESURÉS LE 2026-10-16 QUI DÉCIDENT DE CES TESTS

1. En Kubernetes 1.37, les drapeaux `--oidc-issuer-url` et compagnie
   n'apparaissent plus dans la ligne de commande de l'apiserver. Seule la
   CONFIGURATION STRUCTURÉE existe, passée par `--authentication-config`, en
   `apiVersion: apiserver.config.k8s.io/v1beta1`.

2. Elle REFUSE un issuer en http, mot pour mot : « invalid authentication
   configuration: jwt[0].issuer.url: Invalid value: "http://..." : URL scheme
   must be https ». Le serveur ne démarre pas, et k3d rend un délai dépassé
   sans montrer cette ligne, qui est dans les journaux du conteneur.

3. Keycloak calcule son issuer DEPUIS LA REQUÊTE : la porte HTTP annonce
   `http://127.0.0.1:8080/realms/formation`, la porte TLS annonce
   `https://idp.lab:8443/realms/formation`. Les deux coexistent, et un jeton
   pris par la mauvaise porte est refusé par le cluster avec « You must be
   logged in to the server (Unauthorized) ».

4. Le CA auto-signé passe en PEM INLINE dans `issuer.certificateAuthority`.

5. `kubectl --token` est IGNORÉ si le kubeconfig courant porte un certificat
   client : `auth whoami` répond alors `system:admin` avec `system:masters`, et
   l'on croit que son OIDC fonctionne alors qu'on vient de mesurer son propre
   certificat d'administration. Ces tests passent donc `--kubeconfig /dev/null`
   partout où ils éprouvent un jeton.

6. Sans mappeur de groupes, le compte est AUTHENTIFIÉ et n'a que
   `system:authenticated` : la liaison RBAC existe, et il est quand même
   refusé. C'est le cas d'échec le plus déroutant du lab.

7. `full.path: false` sur le mappeur rend `groups: ["devops"]`, sans chemin. Un
   chemin (`/devops`) ne correspondrait à aucune liaison RBAC écrite sur le nom
   simple.
"""

from __future__ import annotations

import base64
import json
import shlex

import pytest

from conftest import lab_host, lab_target_host

# L'hôte RÉELLEMENT testé. `dsoxlab check --target` peut en imposer un autre,
# et coder le nom en dur ferait tester la cible par défaut en prétendant tester
# celle qu'on a demandée.
CIBLE = lab_target_host("idp.lab")

IDENTIFIANTS = "/opt/iam-lab/identifiants-lab.txt"

#: Les rôles qu'un groupe de la plateforme ne doit JAMAIS porter : ils donnent
#: la machine entière à quiconque entre dans le groupe.
ROLES_INTERDITS = {"cluster-admin", "admin"}


@pytest.fixture(scope="module")
def idp():
    """La machine du lab.

    `lab_host` est une fonction du conftest, pas une fixture : chaque lab bâtit
    la sienne, ce qui permet à un lab multi-hôtes d'en avoir plusieurs.
    """
    return lab_host(CIBLE)


# ── Outils de lecture de l'état ──────────────────────────────────────────────


def _identifiants(hote) -> dict[str, str]:
    fichier = hote.file(IDENTIFIANTS)
    assert fichier.exists, (
        f"{IDENTIFIANTS} est absent. Le setup du lab n'a pas tourné, ou son "
        "script de mise en situation a échoué : la trace est dans "
        "/var/log/dsoxlab-prepare.log sur la machine."
    )
    valeurs = {}
    for ligne in fichier.content_string.splitlines():
        if "=" in ligne and not ligne.startswith("#"):
            clef, _, valeur = ligne.partition("=")
            valeurs[clef.strip()] = valeur.strip()
    return valeurs


def _jeton(hote, ids: dict[str, str], compte: str, *, par_tls: bool = True) -> str:
    """Un jeton d'accès pour `compte`, pris par l'une des deux portes.

    La porte décide de l'issuer, donc de l'acceptation par le cluster. C'est
    tout le sujet du cas d'échec n°3.
    """
    client = ids["CLIENT_KUBE_ATTENDU"]
    mdp = ids["MOT_DE_PASSE"]
    if par_tls:
        base = f"https://idp.lab:8443/realms/{ids['REALM']}"
        tls = f"--cacert {ids['CA_IDP']} --resolve idp.lab:8443:127.0.0.1"
    else:
        base = f"http://127.0.0.1:8080/realms/{ids['REALM']}"
        tls = ""
    res = hote.run(
        f"curl -sS --max-time 20 {tls} -X POST "
        f"{base}/protocol/openid-connect/token "
        f"-d grant_type=password -d client_id={shlex.quote(client)} "
        f"-d username={shlex.quote(compte)} -d password={shlex.quote(mdp)}"
    )
    try:
        charge = json.loads(res.stdout)
    except json.JSONDecodeError:
        pytest.fail(
            "Le point de jeton n'a pas répondu en JSON par la porte "
            f"{'TLS' if par_tls else 'HTTP'} : {res.stdout[:200]!r} "
            f"{res.stderr[:200]!r}"
        )
    return charge.get("access_token", "")


def _charge_utile(jwt: str) -> dict:
    """Le corps d'un JWT, avec le padding exact que base64 attend."""
    corps = jwt.split(".")[1]
    corps += "=" * (-len(corps) % 4)
    return json.loads(base64.urlsafe_b64decode(corps))


def _kubectl(hote, jeton: str, arguments: str):
    """`kubectl` avec le JETON pour seul moyen d'authentification.

    `--kubeconfig /dev/null` n'est pas une précaution de style : sans lui, le
    certificat du contexte courant gagne, et le test mesure le certificat
    d'administration en croyant mesurer l'OIDC (fait n°5).
    """
    return hote.run(
        "kubectl --kubeconfig /dev/null --server https://127.0.0.1:6550 "
        f"--insecure-skip-tls-verify --token {shlex.quote(jeton)} {arguments}"
    )


def _kubectl_admin(hote, cluster: str, arguments: str):
    """`kubectl` en administrateur du cluster, pour LIRE l'état posé.

    Le kubeconfig est RÉGÉNÉRÉ depuis l'état du cluster à chaque appel, et non
    lu dans un `~/.kube/config` : celui-ci appartient au compte qui a créé le
    cluster, et ces tests tournent sous un autre. Un `--context` en dur ne
    trouverait rien si l'apprenant a créé son cluster sous son propre compte,
    et le test accuserait alors le cluster d'être absent.
    """
    return hote.run(
        f"kubectl --kubeconfig \"$(k3d kubeconfig write {shlex.quote(cluster)})\" "
        f"{arguments}")


# ── 1. Le cluster et sa configuration d'authentification ────────────────────


def test_le_cluster_existe_et_son_apiserver_lit_une_configuration(idp):
    """Le cluster tourne, et son apiserver reçoit une config d'authentification.

    On regarde la LIGNE DE COMMANDE du serveur, et non le fichier de
    configuration : un fichier écrit que personne ne lit ne prouve rien, et
    c'est exactement l'erreur que ce lab fait commettre ailleurs.
    """
    ids = _identifiants(idp)
    cluster = ids["CLUSTER_ATTENDU"]

    liste = idp.run("k3d cluster list --no-headers")
    assert cluster in liste.stdout, (
        f"Aucun cluster nommé « {cluster} ». Les tests le cherchent sous ce "
        f"nom exact, que le setup a écrit dans {IDENTIFIANTS}. "
        f"Clusters présents : {liste.stdout.strip()!r}"
    )

    conteneur = f"k3d-{cluster}-server-0"
    cmdline = idp.run(
        f"docker logs {conteneur} 2>&1 | grep -m1 'Running kube-apiserver'"
    ).stdout
    assert cmdline, (
        f"Le conteneur {conteneur} n'a pas journalisé le démarrage de son "
        "apiserver. Le cluster est-il debout ? "
        f"{idp.run(f'docker ps -a --filter name={conteneur} --format \"{{{{.Status}}}}\"').stdout.strip()!r}"
    )
    assert "--authentication-config" in cmdline, (
        "L'apiserver tourne sans `--authentication-config`. En 1.37, les "
        "drapeaux `--oidc-*` n'existent plus : seule la configuration "
        "structurée permet de faire confiance à un fournisseur."
    )


def test_la_configuration_designe_l_idp_en_https_avec_son_ca(idp):
    """L'issuer est la porte TLS de l'IdP, l'audience est demandée, le CA est là.

    L'issuer DOIT être en https : l'apiserver refuse http et ne démarre pas.
    """
    ids = _identifiants(idp)
    chemin = ids["CONF_AUTH_ATTENDUE"]
    fichier = idp.file(chemin)
    assert fichier.exists, (
        f"{chemin} est absent. C'est le fichier que le setup indique dans "
        f"{IDENTIFIANTS} sous CONF_AUTH_ATTENDUE, et celui que l'apiserver "
        "doit lire."
    )
    texte = fichier.content_string

    assert ids["ISSUER_TLS"] in texte, (
        f"La configuration ne désigne pas « {ids['ISSUER_TLS']} ». "
        "Keycloak calcule son issuer depuis la requête : la porte TLS et la "
        "porte HTTP annoncent chacune le sien, et le cluster compare le `iss` "
        "du jeton à ce qui est écrit ici."
    )
    assert ids["ISSUER_HTTP"] not in texte, (
        "La configuration désigne la porte HTTP. L'apiserver refuse un issuer "
        "en http, mot pour mot « URL scheme must be https »."
    )
    assert ids["AUDIENCE_ATTENDUE"] in texte, (
        f"L'audience « {ids['AUDIENCE_ATTENDUE']} » n'est pas demandée. Sans "
        "elle, l'apiserver accepterait un jeton émis pour un autre service du "
        "même realm."
    )
    assert "BEGIN CERTIFICATE" in texte, (
        "Aucun certificat dans la configuration. Le certificat de l'IdP est "
        "auto-signé : l'apiserver doit le connaître pour lire les clefs du "
        "fournisseur, et il l'accepte en PEM inline sous "
        "`issuer.certificateAuthority`."
    )


# ── 2. Le jeton de l'IdP, et ce qu'il porte ─────────────────────────────────


def test_le_cluster_reconnait_le_compte_et_son_groupe(idp):
    """Le jeton de l'IdP authentifie le compte, AVEC son groupe.

    Le groupe est ce qui porte les droits : un compte authentifié sans groupe
    n'a que `system:authenticated`, donc rien.
    """
    ids = _identifiants(idp)
    compte, groupe = ids["COMPTE_DEVOPS"], ids["GROUPE_DEVOPS"]

    jeton = _jeton(idp, ids, compte)
    assert jeton, (
        f"Aucun jeton pour {compte} par la porte TLS. Le client "
        f"« {ids['CLIENT_KUBE_ATTENDU']} » existe-t-il, et autorise-t-il "
        "l'octroi direct par mot de passe ?"
    )

    charge = _charge_utile(jeton)
    assert charge.get("iss") == ids["ISSUER_TLS"], (
        f"Le jeton annonce l'issuer « {charge.get('iss')} » et non "
        f"« {ids['ISSUER_TLS']} »."
    )
    auds = charge.get("aud", [])
    auds = auds if isinstance(auds, list) else [auds]
    assert ids["AUDIENCE_ATTENDUE"] in auds, (
        f"Le jeton ne porte pas l'audience « {ids['AUDIENCE_ATTENDUE']} » "
        f"mais {auds}. Un mappeur d'audience la pose, comme au lab 05."
    )
    assert groupe in (charge.get("groups") or []), (
        f"Le jeton ne porte pas le groupe « {groupe} » : "
        f"groups = {charge.get('groups')!r}. Sans ce claim, le cluster "
        "authentifie le compte et ne lui donne que `system:authenticated`."
    )

    whoami = _kubectl(idp, jeton, "auth whoami")
    assert whoami.rc == 0, (
        "Le cluster n'a pas accepté le jeton de l'IdP :\n"
        f"{whoami.stdout}{whoami.stderr}"
    )
    assert compte in whoami.stdout, (
        f"Le cluster ne voit pas « {compte} » :\n{whoami.stdout}"
    )
    assert groupe in whoami.stdout, (
        f"Le cluster ne voit pas le groupe « {groupe} » :\n{whoami.stdout}\n"
        "Le claim des groupes est-il mis en correspondance dans la "
        "configuration d'authentification ?"
    )


def test_un_jeton_pris_par_la_porte_http_est_refuse(idp):
    """Le MÊME compte, le MÊME mot de passe, et le cluster refuse.

    Seul l'issuer diffère. C'est le cas d'échec que personne ne voit venir :
    le jeton est parfaitement valide, et il n'a pas été émis pour ce cluster.
    """
    ids = _identifiants(idp)
    jeton = _jeton(idp, ids, ids["COMPTE_DEVOPS"], par_tls=False)
    assert jeton, (
        "Aucun jeton par la porte HTTP. Ce test a besoin des deux portes pour "
        "montrer que seule l'une est acceptée."
    )
    assert _charge_utile(jeton).get("iss") == ids["ISSUER_HTTP"], (
        "Le jeton pris par la porte HTTP n'annonce pas l'issuer HTTP : la "
        "mesure ne porte pas sur ce qu'elle croit."
    )

    res = _kubectl(idp, jeton, "get nodes")
    assert res.rc != 0, (
        "Le cluster a ACCEPTÉ un jeton dont l'issuer est la porte HTTP. La "
        "configuration désigne-t-elle deux fournisseurs, ou l'issuer "
        "attendu est-il trop permissif ?"
    )
    assert "Unauthorized" in (res.stdout + res.stderr), (
        "Le refus n'est pas une erreur d'authentification :\n"
        f"{res.stdout}{res.stderr}"
    )


# ── 3. Les droits, qui suivent le groupe ────────────────────────────────────


def test_le_groupe_devops_ecrit_dans_son_namespace_et_pas_ailleurs(idp):
    """Les droits sont bornés : ils suivent le groupe, et s'arrêtent quelque part.

    Un droit d'écriture sur tout le cluster serait plus simple à obtenir et ne
    prouverait rien : ce qui se vérifie ici, c'est la LIMITE.
    """
    ids = _identifiants(idp)
    jeton = _jeton(idp, ids, ids["COMPTE_DEVOPS"])
    namespace = ids["NAMESPACE_ATTENDU"]

    present = _kubectl_admin(
        idp, ids["CLUSTER_ATTENDU"], f"get namespace {namespace} -o name")
    assert present.rc == 0, (
        f"Le namespace « {namespace} » n'existe pas. C'est celui que le setup "
        f"annonce dans {IDENTIFIANTS}, et où l'équipe doit pouvoir écrire."
    )

    dedans = _kubectl(
        idp, jeton,
        f"auth can-i create configmaps --namespace {namespace}")
    assert dedans.stdout.strip() == "yes", (
        f"« {ids['COMPTE_DEVOPS']} » ne peut pas écrire dans « {namespace} » : "
        f"{dedans.stdout.strip()!r}. Le groupe « {ids['GROUPE_DEVOPS']} » "
        "est-il lié à un rôle d'écriture sur ce namespace ?"
    )

    ailleurs = _kubectl(
        idp, jeton, "auth can-i create configmaps --namespace kube-system")
    assert ailleurs.stdout.strip() == "no", (
        f"« {ids['COMPTE_DEVOPS']} » peut écrire dans kube-system : "
        f"{ailleurs.stdout.strip()!r}. Le droit a été accordé sur tout le "
        "cluster au lieu du seul namespace de l'équipe."
    )


def test_le_groupe_lecteurs_lit_et_n_ecrit_pas(idp):
    """La lecture seule est un droit, pas une absence de droit."""
    ids = _identifiants(idp)
    jeton = _jeton(idp, ids, ids["COMPTE_LECTEUR"])
    assert jeton, f"Aucun jeton pour {ids['COMPTE_LECTEUR']}."

    lecture = _kubectl(idp, jeton, "auth can-i list pods --all-namespaces")
    assert lecture.stdout.strip() == "yes", (
        f"« {ids['COMPTE_LECTEUR']} » ne peut pas lire : "
        f"{lecture.stdout.strip()!r}. Le groupe « {ids['GROUPE_LECTEURS']} » "
        "est-il lié à un rôle de lecture ?"
    )

    ecriture = _kubectl(
        idp, jeton,
        f"auth can-i create configmaps --namespace {ids['NAMESPACE_ATTENDU']}")
    assert ecriture.stdout.strip() == "no", (
        f"« {ids['COMPTE_LECTEUR']} » peut écrire : "
        f"{ecriture.stdout.strip()!r}. Un compte de lecture qui écrit n'est "
        "pas un compte de lecture."
    )


def test_aucun_groupe_n_est_lie_a_cluster_admin(idp):
    """Le raccourci qui rend le lab vert et le cluster indéfendable.

    Lier un groupe de l'annuaire à `cluster-admin` donne la machine entière à
    quiconque entre dans ce groupe, et l'entrée dans un groupe n'est plus une
    décision d'administrateur du cluster : c'est une décision d'annuaire.
    """
    ids = _identifiants(idp)
    groupes = {ids["GROUPE_DEVOPS"], ids["GROUPE_LECTEURS"]}

    brut = _kubectl_admin(
        idp, ids["CLUSTER_ATTENDU"], "get clusterrolebindings -o json")
    assert brut.rc == 0, (
        f"Impossible de lire les liaisons du cluster :\n{brut.stderr}"
    )
    fautives = []
    for liaison in json.loads(brut.stdout).get("items", []):
        role = liaison.get("roleRef", {}).get("name", "")
        if role not in ROLES_INTERDITS:
            continue
        for sujet in liaison.get("subjects") or []:
            if sujet.get("kind") == "Group" and sujet.get("name") in groupes:
                fautives.append(f"{liaison['metadata']['name']} -> {role} "
                                f"({sujet['name']})")
    assert not fautives, (
        "Un groupe de l'annuaire est lié à un rôle qui donne tout le "
        f"cluster : {fautives}. Les droits doivent être bornés, et "
        "`cluster-admin` ne se donne pas à un groupe peuplé ailleurs."
    )


# ── 4. L'outil de la plateforme ─────────────────────────────────────────────


def test_l_outil_laisse_entrer_par_l_idp(idp):
    """Le parcours complet, de l'outil à la session, joué sur la machine.

    Ce qui est vérifié n'est pas que l'outil ANNONCE le fournisseur, mais
    qu'il ramène l'utilisateur connecté : une page de connexion qui porte le
    bon bouton et renvoie sur elle-même est le symptôme exact de l'erreur que
    ce lab fait rencontrer.
    """
    ids = _identifiants(idp)
    depart = f"{ids['GRAFANA_URL']}/login/generic_oauth"

    redirection = idp.run(
        f"curl -sS -o /dev/null -D - {shlex.quote(depart)} "
        "| grep -i '^location:'")
    assert "idp.lab:8443" in redirection.stdout, (
        "L'outil ne renvoie pas vers la porte TLS du fournisseur :\n"
        f"{redirection.stdout.strip()!r}\n"
        f"Son fichier d'environnement est {ids['GRAFANA_ENV']}, et le script "
        "qui le relit est dans /opt/iam-lab/outils/."
    )
    assert "code_challenge_method" in redirection.stdout, (
        "La demande d'autorisation ne porte pas de `code_challenge_method`. "
        "Le client exige PKCE, et l'erreur part AU CALLBACK : l'outil "
        "ramènera l'utilisateur sur sa page de connexion sans rien dire."
    )

    res = idp.run(
        f"SSL_CERT_FILE={shlex.quote(ids['CA_IDP'])} timeout 90 python3 -I "
        "/opt/iam-lab/outils/parcours.py "
        f"--depart {shlex.quote(depart)} "
        f"--utilisateur {shlex.quote(ids['COMPTE_DEVOPS'])} "
        f"--mot-de-passe {shlex.quote(ids['MOT_DE_PASSE'])}")
    assert res.rc != 2, (
        "Le témoin de parcours n'a pas pu mesurer, ce qui n'est pas la même "
        f"chose qu'un branchement cassé :\n{res.stdout}{res.stderr}"
    )
    try:
        parcours = json.loads(res.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"Le témoin n'a pas rendu de JSON :\n{res.stdout[:400]}")

    assert parcours["connexion_posee"], (
        "Le parcours n'a jamais rencontré le formulaire de connexion du "
        "fournisseur : l'outil n'a donc pas délégué l'authentification.\n"
        f"étapes : {json.dumps(parcours['etapes'])}"
    )
    assert parcours["http"] == 200, (
        f"Le parcours finit sur HTTP {parcours['http']} à "
        f"{parcours['arrivee']}."
    )
    assert "/login" not in parcours["arrivee"], (
        f"Le parcours revient sur la page de connexion ({parcours['arrivee']}), "
        "ce qui est le symptôme d'une erreur renvoyée au callback. Regardez "
        "les paramètres de l'URL de retour : `error` et `error_description` y "
        "disent ce que le fournisseur a refusé."
    )
