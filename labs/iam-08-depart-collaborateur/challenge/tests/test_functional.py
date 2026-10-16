"""Ce qui reste ouvert après un départ, et ce qui reste pour l'audit.

TROIS FAITS MESURÉS LE 2026-10-16 QUI DÉCIDENT DE CES TESTS

1. LLDAP refuse tout `ldapmodify` : « Server is unwilling to perform (53) », et
   son schéma n'a aucun attribut d'activation. On ne peut donc PAS désactiver un
   compte à la source. La fiche le demandait ; la réalité l'interdit.

2. Un compte FÉDÉRÉ en lecture seule SE LAISSE désactiver dans Keycloak :
   `enabled` est un état local, que le fournisseur garde même quand l'annuaire
   est en lecture seule. C'est la voie qui reste, et elle fonctionne.

3. UNE SESSION SURVIT À LA DÉSACTIVATION. Mesuré : après `enabled = false`, le
   compte compte encore une session active. Le rafraîchissement est refusé
   (« User disabled ») et `userinfo` rend 401, mais la session est là. C'est le
   geste que tout le monde oublie, et la fiche du compte dit « désactivé ».

CE QUE LES TESTS NE PEUVENT PAS PROUVER, ET QUI EST DIT DANS L'ÉNONCÉ

Un access token déjà émis reste SIGNÉ et NON EXPIRÉ après tout cela. Une API qui
le valide hors ligne, comme celle du lab 05, l'accepte jusqu'à son `exp`.
`userinfo` le refuse parce qu'il interroge Keycloak, pas parce que le jeton a
changé. Aucun geste de ce lab ne raccourcit cette fenêtre : seule la durée de
vie des jetons le fait.
"""

from __future__ import annotations

import base64
import json
import time

import pytest

from conftest import lab_host, lab_target_host

# L'hôte RÉELLEMENT testé. `dsoxlab check --target` peut en imposer un autre,
# et coder le nom en dur ferait tester la cible par défaut en prétendant tester
# celle qu'on a demandée.
CIBLE = lab_target_host("idp.lab")

KEYCLOAK = "http://127.0.0.1:8080"
REALM = "formation"
IDENTIFIANTS = "/opt/iam-lab/identifiants-lab.txt"
SECRETS_DU_SOCLE = "/opt/socle-iam/.env"


@pytest.fixture(scope="module")
def idp():
    """La machine du lab.

    `lab_host` est une fonction du conftest, pas une fixture : chaque lab bâtit
    la sienne, ce qui permet à un lab multi-hôtes d'en avoir plusieurs.
    """
    return lab_host(CIBLE)


# ── Outils de lecture de l'état ──────────────────────────────────────────────


def _fichier_en_paires(hote, chemin: str) -> dict[str, str]:
    fichier = hote.file(chemin)
    assert fichier.exists, (
        f"{chemin} est absent. Le setup du lab n'a pas tourné, ou son script de "
        "mise en situation a échoué : la trace est dans "
        "/var/log/dsoxlab-prepare.log sur la machine."
    )
    valeurs = {}
    for ligne in fichier.content_string.splitlines():
        if "=" in ligne and not ligne.startswith("#"):
            clef, _, valeur = ligne.partition("=")
            valeurs[clef.strip()] = valeur.strip()
    return valeurs


def _identifiants(hote) -> dict[str, str]:
    return _fichier_en_paires(hote, IDENTIFIANTS)


def _jeton_admin(hote) -> str:
    """Sans `set -o pipefail` : testinfra exécute par `/bin/sh`, donc `dash`."""
    res = hote.run(
        f"u=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME=' {SECRETS_DU_SOCLE} | cut -d= -f2-); "
        f"p=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD=' {SECRETS_DU_SOCLE} | cut -d= -f2-); "
        f"curl -sS --max-time 20 -X POST {KEYCLOAK}/realms/master/protocol/openid-connect/token "
        "-d grant_type=password -d client_id=admin-cli "
        '-d "username=$u" -d "password=$p" | jq -r \'.access_token // empty\''
    )
    jeton = res.stdout.strip()
    assert jeton, (
        "Aucun jeton d'administration n'a pu être obtenu. Keycloak répond-il "
        f"sur {KEYCLOAK}, et le socle est-il installé ? (rc={res.rc})"
    )
    return jeton


def _api(hote, chemin: str) -> object:
    jeton = _jeton_admin(hote)
    res = hote.run(
        f"curl -sS --max-time 30 '{KEYCLOAK}/admin/{chemin}' "
        f"-H 'Authorization: Bearer {jeton}'"
    )
    if not res.stdout.strip():
        return None
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        pytest.fail(
            f"L'API d'administration n'a pas rendu de JSON pour {chemin} : "
            f"{res.stdout[:300]}"
        )


def _compte(hote, nom: str) -> dict | None:
    trouves = _api(hote, f"realms/{REALM}/users?username={nom}&exact=true") or []
    if not trouves:
        return None
    return _api(hote, f"realms/{REALM}/users/{trouves[0]['id']}")


def _revendications(jeton: str) -> dict:
    charge = jeton.split(".")[1]
    charge += "=" * (-len(charge) % 4)
    return json.loads(base64.urlsafe_b64decode(charge))


# ── Les tests ────────────────────────────────────────────────────────────────


def test_le_compte_existe_toujours(idp):
    """Désactivé, et non supprimé. La traçabilité en dépend.

    Vert avant le travail ? OUI, et c'est assumé : le compte existe au départ.
    Ce test n'est pas là pour noter le travail, il est là pour refuser le
    raccourci. Supprimer un compte fait disparaître le problème ET les
    éléments de l'enquête : qui a fait quoi, sous quel identifiant, et dans
    quels groupes il était le jour de son départ.
    """
    identifiants = _identifiants(idp)
    qui_part = identifiants["QUI_PART"]

    compte = _compte(idp, qui_part)
    assert compte, (
        f"Le compte « {qui_part} » a disparu du realm. Il a été SUPPRIMÉ, et "
        "avec lui la trace de ce qu'il pouvait faire. Un départ se traite par "
        "une désactivation : l'accès est coupé, et l'historique reste "
        "auditable."
    )
    assert compte.get("federationLink"), (
        f"Le compte « {qui_part} » n'est plus rattaché à la fédération. A-t-il "
        "été recréé à la main après une suppression ?"
    )


def test_le_compte_est_desactive(idp):
    """Désactivé dans le fournisseur, faute de pouvoir l'être à la source.

    Vert avant le travail ? Non : le setup vérifie que le compte est ACTIF
    avant de rendre la main.

    L'annuaire ne le permet pas : LLDAP refuse tout `ldapmodify` et n'a aucun
    attribut d'activation. `enabled` est un état que Keycloak garde en local,
    même pour un compte dont l'annuaire est en lecture seule.
    """
    identifiants = _identifiants(idp)
    qui_part = identifiants["QUI_PART"]

    compte = _compte(idp, qui_part)
    assert compte, f"Le compte « {qui_part} » est introuvable."
    assert compte.get("enabled") is False, (
        f"Le compte « {qui_part} » est toujours actif. Il peut donc encore "
        "ouvrir une session, et son mot de passe fonctionne toujours."
    )

    for reste in identifiants["QUI_RESTE"].split():
        autre = _compte(idp, reste)
        assert autre and autre.get("enabled") is True, (
            f"Le compte « {reste} », qui ne part pas, a été désactivé aussi. "
            "Un départ ne coupe les accès que d'une personne."
        )


def test_aucune_session_ne_survit(idp):
    """LE GESTE QUE TOUT LE MONDE OUBLIE.

    Vert avant le travail ? Non : le setup OUVRE une session avant de rendre la
    main, et vérifie qu'elle est là.

    Mesuré le 2026-10-16 : une session SURVIT à la désactivation du compte. La
    fiche du compte dit « désactivé », et la session continue. Il faut la fermer
    explicitement.
    """
    identifiants = _identifiants(idp)
    qui_part = identifiants["QUI_PART"]

    trouves = _api(idp, f"realms/{REALM}/users?username={qui_part}&exact=true") or []
    assert trouves, f"Le compte « {qui_part} » est introuvable."
    sessions = _api(idp, f"realms/{REALM}/users/{trouves[0]['id']}/sessions") or []

    assert not sessions, (
        f"Le compte « {qui_part} » compte encore {len(sessions)} session(s) "
        "active(s). Désactiver un compte ne ferme PAS ses sessions : c'est "
        "mesuré, et c'est le geste qu'on oublie parce que rien ne le signale."
    )


def test_le_jeton_de_rafraichissement_est_refuse(idp):
    """La session fermée se prouve en essayant de la prolonger.

    Vert avant le travail ? Non : le setup dépose un jeton de rafraîchissement
    qui FONCTIONNE, et vérifie la session ouverte.

    Un jeton de rafraîchissement est la façon dont une application prolonge un
    accès sans redemander de mot de passe. S'il fonctionne encore, la personne
    qui part garde l'accès aussi longtemps que son application le rafraîchit.
    """
    identifiants = _identifiants(idp)
    jetons = _fichier_en_paires(idp, identifiants["JETONS_DE_LA_SESSION"])

    res = idp.run(
        f"curl -sS --max-time 20 -X POST "
        f"{KEYCLOAK}/realms/{REALM}/protocol/openid-connect/token "
        "-d grant_type=refresh_token -d client_id=appli-notes "
        f"-d refresh_token={jetons['REFRESH_TOKEN']!r}"
    )
    try:
        reponse = json.loads(res.stdout or "{}")
    except json.JSONDecodeError:
        pytest.fail(f"Réponse illisible du point de jeton : {res.stdout[:300]}")

    assert not reponse.get("access_token"), (
        "Le jeton de rafraîchissement de la personne qui part FONCTIONNE "
        "ENCORE. Son application peut donc prolonger son accès indéfiniment, "
        "sans jamais redemander de mot de passe."
    )
    assert reponse.get("error") == "invalid_grant", (
        f"Le refus n'est pas celui attendu : {reponse!r}. Mesuré sur Keycloak "
        "26.8.1, un compte désactivé rend `invalid_grant` avec « User "
        "disabled », et une session fermée « Session not active »."
    )


def test_les_groupes_ont_ete_retires(idp):
    """Les droits partent avec la personne, et le reste ne bouge pas.

    Vert avant le travail ? Non : le setup met la personne dans un groupe et le
    vérifie.

    Un compte désactivé qui garde ses groupes est un compte qu'une
    réactivation distraite remet en service avec tous ses droits. Et dans une
    revue, il continue d'apparaître comme ayant accès.
    """
    identifiants = _identifiants(idp)
    qui_part = identifiants["QUI_PART"]

    trouves = _api(idp, f"realms/{REALM}/users?username={qui_part}&exact=true") or []
    assert trouves, f"Le compte « {qui_part} » est introuvable."
    groupes = _api(idp, f"realms/{REALM}/users/{trouves[0]['id']}/groups") or []
    assert not groupes, (
        f"Le compte « {qui_part} » appartient encore à "
        f"{[g['name'] for g in groupes]}. Une réactivation distraite lui "
        "rendrait tous ses droits."
    )

    # Et le rôle accordé DIRECTEMENT, hors groupe, qui est celui qu'on oublie.
    role = identifiants["ROLE_DIRECT"]
    attributions = _api(
        idp, f"realms/{REALM}/users/{trouves[0]['id']}/role-mappings"
    ) or {}
    directs = {r["name"] for r in attributions.get("realmMappings") or []}
    assert role not in directs, (
        f"Le compte garde le rôle « {role} », qui lui était accordé "
        "DIRECTEMENT et non par un groupe. C'est celui qu'une revue par "
        "groupes ne voit jamais, et c'est pour cela qu'il est dans ce lab."
    )

    # Les autres gardent les leurs.
    for reste in identifiants["QUI_RESTE"].split():
        autres = _api(idp, f"realms/{REALM}/users?username={reste}&exact=true") or []
        assert autres, f"Le compte « {reste} » est introuvable."
        ses_groupes = _api(
            idp, f"realms/{REALM}/users/{autres[0]['id']}/groups"
        ) or []
        assert ses_groupes, (
            f"Le compte « {reste} », qui ne part pas, a perdu ses groupes. Un "
            "départ ne retire les droits que d'une personne."
        )


def test_le_fichier_de_revue_est_complet_et_a_jour(idp):
    """La preuve que la revue a eu lieu, et qu'elle voit tout.

    Vert avant le travail ? Non : le setup retire le fichier.

    Une revue qui ne listerait que les groupes manquerait les rôles accordés
    directement, qui sont précisément ceux que personne ne surveille. Le
    fichier doit porter les deux, pour chaque compte, et refléter l'état
    APRÈS le départ.
    """
    identifiants = _identifiants(idp)
    chemin = identifiants["FICHIER_DE_REVUE"]
    qui_part = identifiants["QUI_PART"]

    fichier = idp.file(chemin)
    assert fichier.exists, (
        f"{chemin} est absent. La revue fait partie du travail : sans trace "
        "écrite, personne ne peut dire qui avait accès à quoi le jour du "
        "départ."
    )

    try:
        revue = json.loads(fichier.content_string)
    except json.JSONDecodeError as erreur:
        pytest.fail(f"{chemin} n'est pas du JSON lisible : {erreur}")

    # La forme est libre à une condition : qu'on puisse retrouver chaque compte
    # avec ses groupes et ses rôles. On accepte une liste ou un dictionnaire.
    if isinstance(revue, dict) and "comptes" in revue:
        entrees = revue["comptes"]
    else:
        entrees = revue
    assert isinstance(entrees, list), (
        f"{chemin} doit porter une LISTE de comptes, ou un objet avec une clef "
        f"« comptes » qui en contient une. Lu : {type(entrees).__name__}"
    )
    assert entrees, f"{chemin} ne liste aucun compte."

    par_nom = {}
    for entree in entrees:
        assert isinstance(entree, dict), (
            f"Chaque entrée de {chemin} doit être un objet. Lu : {entree!r}"
        )
        nom = entree.get("username") or entree.get("compte") or entree.get("nom")
        assert nom, (
            f"Une entrée de {chemin} ne nomme pas son compte : "
            f"{json.dumps(entree, ensure_ascii=False)[:200]}. Attendu une clef "
            "`username`, `compte` ou `nom`."
        )
        par_nom[nom] = entree

    attendus = set(identifiants["QUI_RESTE"].split()) | {qui_part}
    manquants = sorted(attendus - set(par_nom))
    assert not manquants, (
        f"{chemin} ne liste pas {manquants}. Une revue incomplète ne prouve "
        f"rien. Comptes listés : {sorted(par_nom)}"
    )

    for nom, entree in par_nom.items():
        clefs = set(entree)
        assert clefs & {"groupes", "groups"}, (
            f"L'entrée de « {nom} » ne porte pas de liste de groupes "
            f"(clefs : {sorted(clefs)})."
        )
        assert clefs & {"roles", "rôles", "realmRoles"}, (
            f"L'entrée de « {nom} » ne porte pas de liste de rôles "
            f"(clefs : {sorted(clefs)}). Une revue par groupes seuls manque "
            "les rôles accordés directement, qui sont ceux que personne ne "
            "surveille."
        )

    # La revue doit refléter l'ÉTAT APRÈS LE DÉPART : la personne y figure,
    # sans groupe et sans rôle.
    partante = par_nom[qui_part]
    groupes = partante.get("groupes") or partante.get("groups") or []
    roles = (
        partante.get("roles") or partante.get("rôles")
        or partante.get("realmRoles") or []
    )
    role_direct = identifiants["ROLE_DIRECT"]
    assert not groupes, (
        f"La revue montre « {qui_part} » encore dans {groupes}. Elle a été "
        "écrite AVANT le retrait des groupes : une revue qui décrit un état "
        "révolu est pire qu'aucune revue."
    )
    assert role_direct not in roles, (
        f"La revue montre « {qui_part} » avec le rôle « {role_direct} ». "
        "Elle a été écrite avant le retrait."
    )


def test_la_personne_ne_peut_plus_ouvrir_de_session(idp):
    """Le contrôle de bout en bout : son mot de passe ne sert plus à rien.

    Vert avant le travail ? Non : le setup vérifie qu'une session s'ouvre.

    Tous les tests précédents peuvent passer sans que l'accès soit coupé, par
    exemple si quelque chose a réactivé le compte entre-temps. Ici on essaie
    pour de vrai, avec le mot de passe qui fonctionnait.
    """
    identifiants = _identifiants(idp)
    res = idp.run(
        f"curl -sS --max-time 20 -X POST "
        f"{KEYCLOAK}/realms/{REALM}/protocol/openid-connect/token "
        "-d grant_type=password -d client_id=appli-notes -d scope=openid "
        f"-d username={identifiants['QUI_PART']} "
        f"-d password={identifiants['MOT_DE_PASSE']!r}"
    )
    try:
        reponse = json.loads(res.stdout or "{}")
    except json.JSONDecodeError:
        pytest.fail(f"Réponse illisible du point de jeton : {res.stdout[:300]}")

    assert not reponse.get("access_token"), (
        "La personne qui part obtient encore un jeton avec son mot de passe. "
        "Rien n'est coupé."
    )

    # Et quelqu'un qui reste doit toujours pouvoir entrer : couper trop large
    # est aussi une faute, et celle-là se remarque le lundi matin.
    reste = identifiants["QUI_RESTE"].split()[0]
    res = idp.run(
        f"curl -sS --max-time 20 -X POST "
        f"{KEYCLOAK}/realms/{REALM}/protocol/openid-connect/token "
        "-d grant_type=password -d client_id=appli-notes -d scope=openid "
        f"-d username={reste} "
        f"-d password={identifiants['MOT_DE_PASSE']!r}"
    )
    reponse = json.loads(res.stdout or "{}")
    assert reponse.get("access_token"), (
        f"Le compte « {reste} », qui ne part pas, ne peut plus se connecter "
        f"({reponse.get('error')} : {reponse.get('error_description')}). Un "
        "départ ne coupe les accès que d'une personne."
    )
    # Le jeton obtenu est bien frais : sans cette vérification, un jeton mis en
    # cache pourrait faire passer le test.
    assert _revendications(reponse["access_token"])["iat"] >= int(time.time()) - 120, (
        "Le jeton obtenu n'est pas récent, ce qui est inattendu."
    )
