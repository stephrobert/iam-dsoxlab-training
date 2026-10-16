"""iam-02-keycloak-installer : ce que le serveur rend vraiment.

LA QUESTION POSÉE À CHAQUE TEST

« Serait-il vert si l'apprenant ne faisait rien ? » Si oui, ce n'est pas un
test, c'est une hypothèse du setup. Trois tests de ce lab ont dû être écrits
autrement pour y répondre non, et c'est noté sur chacun.

Le piège le plus net est le compte de démarrage. La fiche demande de vérifier
que l'administrateur temporaire « n'existe plus ou est désactivé ». Écrit
naïvement, ce test est VERT AVANT LE TRAVAIL : sur une machine où Keycloak ne
tourne pas, aucun compte de démarrage n'existe non plus. La forme juste exige
d'abord que le serveur fonctionne, puis que ce compte-là n'obtienne plus rien.

CE QUE LES TESTS N'INTERROGENT JAMAIS

Le contenu du fichier Compose de l'apprenant. Il arrive au résultat par le
chemin qu'il veut, et un `grep` sur son fichier ne prouverait pas que le
serveur a compris ce qu'il a écrit. On interroge donc l'API d'administration,
les points d'accès OIDC et le port de gestion.
"""

from __future__ import annotations

import json

import pytest

from conftest import lab_host, lab_target_host, message

# L'hôte RÉELLEMENT testé. `dsoxlab check --target` peut en imposer un autre,
# et coder le nom en dur ferait tester la cible par défaut en prétendant
# tester celle qu'on a demandée.
CIBLE = lab_target_host("idp.lab")

TRAVAIL = "/opt/keycloak-lab"
REALM = "formation"
# Le port de gestion, où vivent la santé et les métriques. Ce n'est pas celui
# de l'application, et les confondre est une erreur fréquente : la fiche du lab
# en fait un indice.
PORT_GESTION = 9000
PORT_APP = 8080


@pytest.fixture(scope="module")
def idp():
    """La machine du lab.

    `lab_host` est une fonction du conftest, pas une fixture : chaque lab
    bâtit la sienne, ce qui permet à un lab multi-hôtes d'en avoir plusieurs.
    """
    return lab_host(CIBLE)


# ── Outils de lecture de l'état ──────────────────────────────────────────────

def _identifiants(idp) -> dict[str, str]:
    """Le compte nominatif que le setup a imposé, lu sur la machine.

    Imposé parce que les tests doivent pouvoir s'authentifier, et généré par le
    setup parce qu'aucun secret ne vit dans le dépôt.
    """
    fichier = idp.file(f"{TRAVAIL}/identifiants.txt")
    assert fichier.exists, message(
        en=f"{TRAVAIL}/identifiants.txt has disappeared. That file is placed by the "
        "lab's setup and carries the administration account to create. Run "
        "`dsoxlab run iam-02-keycloak-installer` again to get the starting "
        "situation back.",
        fr=f"{TRAVAIL}/identifiants.txt a disparu. Ce fichier est posé par le "
        "setup du lab et porte le compte d'administration à créer. Rejouez "
        "`dsoxlab run iam-02-keycloak-installer` pour retrouver la situation "
        "de départ.",
    )
    valeurs = {}
    for ligne in fichier.content_string.splitlines():
        if "=" in ligne and not ligne.startswith("#"):
            cle, _, val = ligne.partition("=")
            valeurs[cle.strip()] = val.strip()
    return valeurs


def _curl_json(idp, url: str, *args: str) -> tuple[int, dict | None]:
    """Un appel HTTP depuis la machine, et son code de retour séparé du corps.

    `curl` y est installé par la couche machine du socle. On lit le code et le
    corps en une fois, parce qu'un test qui ne regarde que le corps ne
    distingue pas « refusé » de « répond mal ».

    Le corps passe par un fichier que `mktemp` nomme, et non par un chemin
    fixe : deux tests qui tourneraient en parallèle se marcheraient dessus, et
    le second lirait la réponse du premier sans que rien ne le signale.
    """
    res = idp.run(
        "f=$(mktemp); "
        + " ".join(["curl", "-s", "-o", '"$f"', "-w", "'%{http_code}'", *args, f"'{url}'"])
        + '; echo; cat "$f"; rm -f "$f"'
    )
    lignes = res.stdout.split("\n", 1)
    try:
        code = int(lignes[0].strip() or 0)
    except ValueError:
        return 0, None
    corps_brut = lignes[1] if len(lignes) > 1 else ""
    try:
        return code, json.loads(corps_brut) if corps_brut.strip() else None
    except json.JSONDecodeError:
        return code, None


def _jeton(idp, utilisateur: str, motdepasse: str, realm: str) -> str | None:
    """Un jeton d'accès, ou None si l'authentification est refusée.

    C'est la mesure la plus forte dont on dispose : un compte qui obtient un
    jeton est un compte qui fonctionne, quoi que dise la configuration.
    """
    code, corps = _curl_json(
        idp,
        f"http://127.0.0.1:{PORT_APP}/realms/{realm}/protocol/openid-connect/token",
        "-X", "POST",
        "-d", "grant_type=password",
        "-d", "client_id=admin-cli",
        "-d", f"username={utilisateur}",
        "-d", f"password={motdepasse}",
    )
    if code != 200 or not corps:
        return None
    return corps.get("access_token")


# ── Les tests ────────────────────────────────────────────────────────────────

def test_keycloak_repond_et_sa_sante_est_au_vert(idp):
    """Le point de santé, sur le port de GESTION.

    Vert avant le travail ? Non : le setup vérifie qu'aucun service n'écoute
    sur 8080 ni 9000, et refuse de poser la situation si l'un répond.
    """
    code, corps = _curl_json(idp, f"http://127.0.0.1:{PORT_GESTION}/health/ready")
    assert code == 200, message(
        en=f"Keycloak's health endpoint does not answer on port "
        f"{PORT_GESTION} (HTTP code {code}). Health does not live on the "
        f"application's port but on the management port, and it must be "
        f"enabled to be served.",
        fr=f"Le point de santé de Keycloak ne répond pas sur le port "
        f"{PORT_GESTION} (code HTTP {code}). La santé ne vit pas sur le port "
        f"de l'application mais sur le port de gestion, et elle doit être "
        f"activée pour être servie.",
    )
    assert corps and corps.get("status") == "UP", message(
        en=f"Keycloak answers on its management port but does not declare itself ready: "
        f"{corps}. Look at its logs, it names what it is missing.",
        fr=f"Keycloak répond sur son port de gestion mais ne se déclare pas prêt : "
        f"{corps}. Regardez ses journaux, il nomme ce qui lui manque.",
    )


def test_la_base_est_postgresql_et_non_celle_de_developpement(idp):
    """La base réellement en service, demandée au serveur.

    Vert avant le travail ? Non : sans Keycloak, il n'y a rien à interroger.

    On ne lit pas le fichier Compose de l'apprenant : il pourrait déclarer
    PostgreSQL et lancer `start-dev`, qui ignore la configuration de base et
    reprend sa base en fichier. Seul le serveur sait ce qu'il utilise, et il le
    dit dans sa configuration effective.
    """
    res = idp.run(
        "docker ps --format '{{.Names}}' | while read -r c; do "
        "docker exec \"$c\" /opt/keycloak/bin/kc.sh show-config 2>/dev/null "
        "| grep -E '^.*(db|db-url) =' && break; done"
    )
    configuration = res.stdout.lower()
    assert configuration, message(
        en="No container returns its Keycloak configuration. Is the server "
        "running, and is it really Keycloak's image?",
        fr="Aucun conteneur ne rend sa configuration Keycloak. Le serveur "
        "tourne-t-il, et est-ce bien l'image de Keycloak ?",
    )
    assert "dev-file" not in configuration and "dev-mem" not in configuration, message(
        en="Keycloak uses its DEVELOPMENT database. That is what "
        "`start-dev` does: it ignores the declared database and keeps its "
        "own, in a file, which goes away with the container. Production mode expects "
        "`start`.\nConfiguration read:\n" + res.stdout,
        fr="Keycloak utilise sa base de DÉVELOPPEMENT. C'est ce que fait "
        "`start-dev` : il ignore la base déclarée et garde la sienne, en "
        "fichier, qui part avec le conteneur. Le mode production attend "
        "`start`.\nConfiguration lue :\n" + res.stdout,
    )
    assert "postgres" in configuration, message(
        en="The database in service is not PostgreSQL.\nConfiguration read:\n" + res.stdout,
        fr="La base en service n'est pas PostgreSQL.\nConfiguration lue :\n" + res.stdout,
    )


def test_le_realm_formation_existe_et_sert_ses_points_d_acces(idp):
    """Le realm, vu de l'extérieur comme une application le verrait.

    Vert avant le travail ? Non : le realm n'existe pas sur une machine nue, et
    ce lab est le seul du catalogue dont le setup n'installe pas le socle, donc
    aucun realm n'est hérité.

    On interroge la découverte OIDC plutôt que l'API d'administration : c'est
    ce qu'une application consomme, et cela prouve que le realm est servi, pas
    seulement enregistré.
    """
    code, corps = _curl_json(
        idp,
        f"http://127.0.0.1:{PORT_APP}/realms/{REALM}/.well-known/openid-configuration",
    )
    assert code == 200, message(
        en=f"The realm \"{REALM}\" does not serve its OIDC discovery (HTTP code "
        f"{code}). A missing realm returns 404: check its name, which must be "
        f"\"{REALM}\" exactly.",
        fr=f"Le realm « {REALM} » ne sert pas sa découverte OIDC (code HTTP "
        f"{code}). Un realm absent rend 404 : vérifiez son nom, qui doit être "
        f"« {REALM} » exactement.",
    )
    assert corps and "token_endpoint" in corps, message(
        en=f"The realm \"{REALM}\" answers but its discovery carries no "
        f"`token_endpoint`: {corps}",
        fr=f"Le realm « {REALM} » répond mais sa découverte ne porte pas de "
        f"`token_endpoint` : {corps}",
    )


def test_l_administrateur_nominatif_obtient_un_jeton(idp):
    """Le compte nominatif fonctionne vraiment, dans le realm maître.

    Vert avant le travail ? Non : le compte n'existe pas, et aucun serveur ne
    pourrait le lui dire.

    L'administrateur d'un serveur Keycloak vit dans le realm `master`, pas dans
    le realm applicatif : c'est une confusion fréquente, et le message
    d'échec la nomme.
    """
    ids = _identifiants(idp)
    jeton = _jeton(idp, ids["ADMIN_UTILISATEUR"], ids["ADMIN_MOTDEPASSE"], "master")
    assert jeton, message(
        en=f"The account \"{ids['ADMIN_UTILISATEUR']}\" does not obtain a token in "
        f"the `master` realm. The SERVER's administrator lives there, and not in the "
        f"application realm: an account created in \"{REALM}\" administers that "
        f"realm, not the server. The expected password is the one in "
        f"{TRAVAIL}/identifiants.txt.",
        fr=f"Le compte « {ids['ADMIN_UTILISATEUR']} » n'obtient pas de jeton dans "
        f"le realm `master`. L'administrateur du SERVEUR y vit, et non dans le "
        f"realm applicatif : un compte créé dans « {REALM} » administre ce "
        f"realm, pas le serveur. Le mot de passe attendu est celui de "
        f"{TRAVAIL}/identifiants.txt.",
    )


def test_le_compte_de_demarrage_ne_sert_plus_mais_le_serveur_fonctionne(idp):
    """Le compte temporaire est hors service, ET le serveur marche toujours.

    LES DEUX MOITIÉS SONT DANS LE MÊME TEST, ET C'EST LE SUJET.

    Écrit comme la fiche l'énonce, « l'administrateur temporaire n'existe plus
    ou est désactivé » serait VERT AVANT LE TRAVAIL : sur une machine où
    Keycloak ne tourne pas, ce compte n'existe pas davantage. Le test ne
    mesurerait rien.

    La forme juste exige d'abord que l'administrateur NOMINATIF fonctionne,
    donc que le serveur rende son service, puis que le compte de démarrage ne
    puisse plus rien. C'est ce qui distingue un durcissement d'une panne : un
    serveur arrêté ferme le compte temporaire aussi sûrement qu'une suppression
    bien faite.
    """
    ids = _identifiants(idp)

    nominatif = _jeton(idp, ids["ADMIN_UTILISATEUR"], ids["ADMIN_MOTDEPASSE"], "master")
    assert nominatif, message(
        en="The named account does not obtain a token: the server is not rendering "
        "its service, and removing the bootstrap account would therefore prove "
        "nothing. Make the named administrator work first.",
        fr="Le compte nominatif n'obtient pas de jeton : le serveur ne rend pas "
        "son service, et retirer le compte de démarrage ne prouverait donc "
        "rien. Faites d'abord fonctionner l'administrateur nominatif.",
    )

    # Le nom du compte de démarrage est celui que l'énoncé fait déclarer. On
    # interroge l'API avec le compte nominatif, ce qui est la seule façon
    # honnête de voir si l'autre existe encore et dans quel état.
    code, comptes = _curl_json(
        idp,
        f"http://127.0.0.1:{PORT_APP}/admin/realms/master/users?username=temp-admin&exact=true",
        "-H", f"'Authorization: Bearer {nominatif}'",
    )
    assert code == 200, message(
        en=f"The administration API refuses the list of accounts of the `master` realm "
        f"(HTTP code {code}) although the named account did obtain a token. "
        f"Does that account really have the server's administration role?",
        fr=f"L'API d'administration refuse la liste des comptes du realm `master` "
        f"(code HTTP {code}) alors que le compte nominatif a obtenu un jeton. "
        f"Ce compte a-t-il bien le rôle d'administration du serveur ?",
    )

    restants = [c for c in (comptes or []) if c.get("username") == "temp-admin"]
    if restants:
        assert restants[0].get("enabled") is False, message(
            en="The bootstrap account \"temp-admin\" still exists and it is "
            "ACTIVE. A bootstrap account left active is one more "
            "administration account, whose password went through an "
            "environment variable visible in the container's inspection. "
            "Delete it, or disable it.",
            fr="Le compte de démarrage « temp-admin » existe encore et il est "
            "ACTIF. Un compte de démarrage laissé actif est un compte "
            "d'administration de plus, dont le mot de passe est passé par une "
            "variable d'environnement visible dans l'inspection du conteneur. "
            "Supprimez-le, ou désactivez-le.",
        )


def test_le_realm_survit_au_redemarrage_des_conteneurs(idp):
    """La persistance, éprouvée en redémarrant pour de vrai.

    Vert avant le travail ? Non, et c'est le test qui distingue ce lab d'une
    simple installation : une base embarquée répond aussi bien qu'une base
    externe jusqu'au premier redémarrage.

    On ne lit pas la déclaration de volume du Compose : un volume déclaré au
    mauvais endroit est un volume inutile, et PostgreSQL 18 a justement changé
    le chemin où il attend ses données. Seul un redémarrage tranche.

    Ce test est volontairement le dernier : il coûte une minute, et le jouer
    avant les autres retarderait leurs messages d'échec.
    """

    avant = _curl_json(
        idp, f"http://127.0.0.1:{PORT_APP}/realms/{REALM}/.well-known/openid-configuration"
    )[0]
    assert avant == 200, message(
        en=f"The realm \"{REALM}\" does not answer before the restart: this test can "
        f"measure nothing. Make the previous tests pass first.",
        fr=f"Le realm « {REALM} » ne répond pas avant le redémarrage : ce test ne "
        f"peut rien mesurer. Faites d'abord passer les tests précédents.",
    )

    redemarrage = idp.run(
        f"cd {TRAVAIL} && docker compose restart 2>&1 | tail -3"
    )
    assert redemarrage.rc == 0, message(
        en=f"Restarting the containers failed from {TRAVAIL}: "
        f"{redemarrage.stdout}{redemarrage.stderr}\nIs the Compose file really "
        f"named `compose.yaml` and placed in that directory?",
        fr=f"Le redémarrage des conteneurs a échoué depuis {TRAVAIL} : "
        f"{redemarrage.stdout}{redemarrage.stderr}\nLe fichier Compose est-il "
        f"bien nommé `compose.yaml` et placé dans ce répertoire ?",
    )

    # Keycloak met du temps à revenir : on lui laisse une marge bornée plutôt
    # que de conclure sur un refus de connexion qui ne dirait rien.
    attente = idp.run(
        "for i in $(seq 1 60); do "
        f"  curl -sf http://127.0.0.1:{PORT_APP}/realms/{REALM}/.well-known/openid-configuration "
        "    >/dev/null 2>&1 && echo PRET && break; "
        "  sleep 5; "
        "done"
    )
    assert "PRET" in attente.stdout, message(
        en=f"After the restart, the realm \"{REALM}\" does not come back within five "
        f"minutes. That is the symptom of a database that does not survive: "
        f"`start-dev` keeps its data inside the container, and a volume mounted "
        f"at the wrong path keeps nothing. The database's logs say "
        f"so.",
        fr=f"Après redémarrage, le realm « {REALM} » ne revient pas en cinq "
        f"minutes. C'est le symptôme d'une base qui ne survit pas : "
        f"`start-dev` garde ses données dans le conteneur, et un volume monté "
        f"au mauvais chemin ne conserve rien. Les journaux de la base le "
        f"disent.",
    )
