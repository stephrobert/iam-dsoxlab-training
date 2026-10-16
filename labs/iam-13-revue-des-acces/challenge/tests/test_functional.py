"""L'API qui répond, le workflow qui désactive, et l'accès que personne n'a
justifié.

QUATRE FAITS MESURÉS LE 2026-10-16 QUI DÉCIDENT DE CES TESTS

1. `SCIM_API` est déclarée activée au niveau du serveur, et l'API rend pourtant
   404. Elle s'ouvre par realm, avec `scimApiEnabled` posé À LA RACINE de la
   représentation du realm. Dans ses `attributes`, le PUT rend 204 et la valeur
   relue reste `false`.

2. Une fois ouverte, l'API rend 401 avec des messages SCIM structurés. Le jeton
   d'administration du realm `master` donne « Bearer token required » ; un jeton
   de client du realm donne « Invalid token audience ».

3. L'audience qu'elle attend est l'URL DE L'API ELLE-MÊME :
   `http://127.0.0.1:8080/realms/formation/scim/v2`. C'est exactement la
   compétence du mappeur d'audience du lab 05, réemployée.

4. L'API des workflows rend du YAML, pas du JSON. Un `POST {}` répond
   « Workflow name cannot be null or empty », et
   `{"name": "x", "steps": [{"uses": "disable-user"}]}` rend 201.
"""

from __future__ import annotations

import json

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

#: Les étapes de workflow qui DÉTRUISENT au lieu de désactiver.
ETAPES_DESTRUCTRICES = {"delete-user", "remove-user", "purge-user"}


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


def _brut(hote, chemin: str) -> str:
    """La réponse telle quelle : l'API des workflows rend du YAML."""
    jeton = _jeton_admin(hote)
    res = hote.run(
        f"curl -sS --max-time 30 '{KEYCLOAK}/admin/{chemin}' "
        f"-H 'Authorization: Bearer {jeton}'"
    )
    return res.stdout


def _client(hote, nom: str) -> dict:
    trouves = _api(hote, f"realms/{REALM}/clients?clientId={nom}") or []
    assert trouves, (
        f"Aucun client « {nom} » dans le realm « {REALM} ». L'API SCIM a "
        "besoin d'un client qui s'authentifie pour elle."
    )
    return trouves[0]


def _jeton_du_client_scim(hote) -> str:
    """Un jeton du client que l'apprenant a déclaré, en client credentials."""
    identifiants = _identifiants(hote)
    nom = identifiants["CLIENT_SCIM_ATTENDU"]
    client = _client(hote, nom)
    secret = _api(hote, f"realms/{REALM}/clients/{client['id']}/client-secret")
    valeur = (secret or {}).get("value", "")
    assert valeur, (
        f"Le client « {nom} » n'a pas de secret. Un accès machine passe par un "
        "client CONFIDENTIEL."
    )
    res = hote.run(
        f"curl -sS --max-time 20 -X POST "
        f"{KEYCLOAK}/realms/{REALM}/protocol/openid-connect/token "
        f"-d grant_type=client_credentials -d client_id={nom} "
        f"-d client_secret={valeur!r} | jq -r '.access_token // empty'"
    )
    jeton = res.stdout.strip()
    assert jeton, (
        f"Le client « {nom} » n'obtient pas de jeton en client credentials. Son "
        "compte de service est-il activé ?"
    )
    return jeton


def _scim(hote, chemin: str, methode: str = "GET") -> tuple[int, str]:
    jeton = _jeton_du_client_scim(hote)
    identifiants = _identifiants(hote)
    res = hote.run(
        f"curl -sS --max-time 20 -o /tmp/scim-test -w '%{{http_code}}' "
        f"-X {methode} '{identifiants['URL_SCIM']}/{chemin}' "
        f"-H 'Authorization: Bearer {jeton}'; echo; cat /tmp/scim-test"
    )
    morceaux = res.stdout.split("\n", 1)
    code = morceaux[0].strip()
    assert code.isdigit(), (
        f"L'API SCIM n'a pas répondu : {res.stdout[:300]}"
    )
    return int(code), (morceaux[1] if len(morceaux) > 1 else "")


# ── Les tests ────────────────────────────────────────────────────────────────


def test_l_api_scim_est_ouverte_sur_le_realm(idp):
    """Ouverte PAR REALM, et non par le serveur.

    Vert avant le travail ? Non : le setup la referme et vérifie qu'elle rend
    404 avant de rendre la main.

    Mesuré le 2026-10-16 : la fonctionnalité est déclarée activée au niveau du
    serveur, et l'API rend pourtant 404 tant que le realm ne l'ouvre pas. Le
    drapeau se pose à la RACINE de la représentation du realm ; dans ses
    `attributes`, le PUT réussit et la valeur relue reste fausse.
    """
    realm = _api(idp, f"realms/{REALM}")
    assert isinstance(realm, dict), f"Le realm « {REALM} » est introuvable."
    assert realm.get("scimApiEnabled") is True, (
        "Le realm ne déclare pas l'API SCIM ouverte "
        f"(scimApiEnabled = {realm.get('scimApiEnabled')!r}). Attention à "
        "l'endroit : ce drapeau vit à la RACINE de la représentation du realm, "
        "pas dans ses `attributes`."
    )

    identifiants = _identifiants(idp)
    res = idp.run(
        "curl -sS --max-time 10 -o /dev/null -w '%{http_code}' "
        f"'{identifiants['URL_SCIM']}/ServiceProviderConfig'"
    )
    code = res.stdout.strip()
    assert code != "404", (
        "L'API SCIM rend toujours 404 : elle n'est pas servie. Le drapeau est "
        "peut-être posé au mauvais endroit."
    )
    assert code == "401", (
        f"Sans jeton, l'API SCIM devrait rendre 401 ; elle rend {code}. Une API "
        "de provisionnement qui répond sans authentification est une porte "
        "d'administration ouverte."
    )


def test_le_client_scim_est_confidentiel_et_borne(idp):
    """Un accès machine, confidentiel, et avec les seuls droits qu'il faut.

    Vert avant le travail ? Non : le setup retire ce client.

    Cette API crée et désactive des comptes. Le client qui s'en sert est une
    cible : public, il serait utilisable par quiconque ; avec les droits
    d'administration du realm, il pourrait tout faire.
    """
    identifiants = _identifiants(idp)
    client = _client(idp, identifiants["CLIENT_SCIM_ATTENDU"])

    assert client.get("publicClient") is False, (
        "Le client SCIM est public : n'importe qui pourrait s'en servir pour "
        "créer des comptes."
    )
    assert client.get("serviceAccountsEnabled") is True, (
        "Le client SCIM n'a pas de compte de service, donc il ne peut pas "
        "s'authentifier sans utilisateur."
    )
    assert client.get("standardFlowEnabled") is False, (
        "Le flux de code d'autorisation est ouvert sur un client machine, ce "
        "qui n'a pas de sens : personne ne se connecte avec lui."
    )

    compte_de_service = _api(
        idp, f"realms/{REALM}/clients/{client['id']}/service-account-user")
    assert compte_de_service and compte_de_service.get("id"), (
        "Le compte de service du client SCIM est introuvable."
    )
    attributions = _api(
        idp,
        f"realms/{REALM}/users/{compte_de_service['id']}/role-mappings") or {}
    tous = set()
    for bloc in (attributions.get("clientMappings") or {}).values():
        tous |= {r["name"] for r in bloc.get("mappings") or []}
    assert tous & {"manage-users", "view-users", "query-users"}, (
        "Le compte de service du client SCIM n'a aucun droit sur les comptes "
        f"(rôles de client : {sorted(tous)}). Il ne pourra rien provisionner."
    )
    assert "realm-admin" not in tous, (
        "Le compte de service porte `realm-admin`, qui donne tout. Une API de "
        "provisionnement n'a pas besoin d'administrer le realm."
    )


def test_l_api_scim_accepte_le_jeton_du_client(idp):
    """LE POINT QUI COÛTE UNE APRÈS-MIDI.

    Vert avant le travail ? Non : sans client ni audience, l'appel est refusé.

    Mesuré le 2026-10-16 : l'API rend 401 « Invalid token audience » pour un
    jeton de client ordinaire, et 401 « Bearer token required » pour un jeton
    d'administration du realm master. L'audience qu'elle attend est l'URL DE
    L'API ELLE-MÊME, et elle s'obtient par un mappeur d'audience sur le client,
    exactement comme au lab 05.
    """
    code, corps = _scim(idp, "ServiceProviderConfig")

    if code == 401:
        detail = ""
        try:
            detail = json.loads(corps).get("detail", "")
        except json.JSONDecodeError:
            detail = corps[:120]
        pytest.fail(
            f"L'API SCIM refuse le jeton du client : « {detail} ». Si elle "
            "parle d'audience, le jeton n'en porte pas la bonne : l'API attend "
            "SA PROPRE URL comme audience, et un mappeur d'audience sur le "
            "client la lui donne."
        )
    assert code == 200, (
        f"L'API SCIM rend {code} au lieu de 200 : {corps[:250]}"
    )
    assert "ServiceProviderConfig" in corps, (
        f"La réponse n'est pas celle attendue : {corps[:250]}"
    )


def test_un_compte_a_ete_provisionne_par_l_api(idp):
    """Un compte créé par l'API, et non à la main.

    Vert avant le travail ? Non : le setup retire ce compte.

    Le test le relit PAR SCIM : un compte créé à la main dans la console
    existerait aussi, mais le relire par l'API prouve que l'API fonctionne dans
    les deux sens, ce qui est le but du provisionnement.
    """
    identifiants = _identifiants(idp)
    attendu = identifiants["COMPTE_A_PROVISIONNER"]

    trouves = _api(idp, f"realms/{REALM}/users?username={attendu}&exact=true") or []
    assert trouves, (
        f"Aucun compte « {attendu} » dans le realm. Le challenge demande de le "
        "provisionner PAR l'API SCIM."
    )

    code, corps = _scim(idp, f"Users?filter=userName%20eq%20%22{attendu}%22")
    assert code == 200, (
        f"L'API SCIM ne rend pas la liste des comptes (HTTP {code}) : "
        f"{corps[:250]}"
    )
    assert attendu in corps, (
        f"L'API SCIM ne connaît pas « {attendu} », alors que l'API "
        f"d'administration le voit. Réponse : {corps[:250]}"
    )

    compte = _api(idp, f"realms/{REALM}/users/{trouves[0]['id']}")
    assert compte.get("enabled") is True, (
        f"Le compte « {attendu} » est désactivé à sa création : un compte "
        "provisionné doit pouvoir servir."
    )
    assert compte.get("email"), (
        f"Le compte « {attendu} » n'a pas d'adresse. Un compte sans adresse ne "
        "reçoit ni invitation ni réinitialisation."
    )


def test_un_workflow_desactive_au_lieu_de_supprimer(idp):
    """Le cas d'échec que la fiche nomme, et il est irréversible.

    Vert avant le travail ? Non : le setup retire les workflows et vérifie
    qu'il n'en reste aucun.

    Un workflow qui supprime un compte inactif détruit la traçabilité en même
    temps que l'accès. Et il la détruit tout seul, la nuit, sans que personne
    décide.

    Mesuré le 2026-10-16 : l'API des workflows rend du YAML, pas du JSON.
    """
    brut = _brut(idp, f"realms/{REALM}/workflows")
    assert brut.strip() not in ("", "--- []", "[]"), (
        "Aucun workflow dans le realm. Le challenge en demande un, qui "
        "désactive un compte inactif."
    )

    minuscule = brut.lower()
    destructrices = sorted(e for e in ETAPES_DESTRUCTRICES if e in minuscule)
    assert not destructrices, (
        f"Un workflow emploie {destructrices}, qui DÉTRUIT le compte. La "
        "traçabilité disparaît avec l'accès, et elle disparaît toute seule, "
        "sans que personne décide. Un cycle de vie désactive.\n\n"
        f"Workflows lus :\n{brut[:400]}"
    )
    assert "disable-user" in minuscule, (
        "Aucun workflow ne désactive de compte. Celui qui est demandé doit "
        f"employer une étape de désactivation.\n\nWorkflows lus :\n{brut[:400]}"
    )


def test_la_revue_trouve_l_acces_injustifie(idp):
    """La revue sert à trouver, pas à cocher.

    Vert avant le travail ? Non : le setup retire le fichier et accorde le rôle.

    Le setup a accordé un rôle au nom explicite à quelqu'un de l'équipe de
    lecture, directement sur son compte. Aucune revue par groupes ne le
    montrerait. Le travail est de le trouver ET de le retirer.
    """
    identifiants = _identifiants(idp)
    chemin = identifiants["FICHIER_DE_REVUE"]
    role = identifiants["ROLE_INJUSTIFIE"]
    porteur = identifiants["PORTEUR_DU_ROLE"]

    fichier = idp.file(chemin)
    assert fichier.exists, (
        f"{chemin} est absent. La revue fait partie du travail : sans trace "
        "écrite, personne ne peut dire qui avait accès à quoi."
    )
    try:
        revue = json.loads(fichier.content_string)
    except json.JSONDecodeError as erreur:
        pytest.fail(f"{chemin} n'est pas du JSON lisible : {erreur}")

    entrees = revue["comptes"] if isinstance(revue, dict) and "comptes" in revue \
        else revue
    assert isinstance(entrees, list) and entrees, (
        f"{chemin} doit porter une liste de comptes non vide."
    )

    par_nom = {}
    for entree in entrees:
        nom = entree.get("username") or entree.get("compte") or entree.get("nom")
        assert nom, (
            f"Une entrée de {chemin} ne nomme pas son compte : "
            f"{json.dumps(entree, ensure_ascii=False)[:200]}"
        )
        par_nom[nom] = entree

    attendus = set(identifiants["COMPTES"].split())
    manquants = sorted(attendus - set(par_nom))
    assert not manquants, (
        f"{chemin} ne liste pas {manquants}. Une revue incomplète ne prouve "
        f"rien. Comptes listés : {sorted(par_nom)}"
    )
    for nom, entree in par_nom.items():
        clefs = set(entree)
        assert clefs & {"roles", "rôles", "realmRoles"}, (
            f"L'entrée de « {nom} » ne porte pas de liste de rôles "
            f"(clefs : {sorted(clefs)}). C'est là que l'accès injustifié se "
            "trouve, et une revue par groupes seuls ne le verrait pas."
        )

    # ET LE RÔLE DOIT AVOIR DISPARU, dans le realm comme dans la revue.
    attributions = _api(
        idp,
        f"realms/{REALM}/users/"
        f"{(_api(idp, f'realms/{REALM}/users?username={porteur}&exact=true') or [{}])[0].get('id')}"
        "/role-mappings",
    ) or {}
    directs = {r["name"] for r in attributions.get("realmMappings") or []}
    assert role not in directs, (
        f"Le compte « {porteur} » porte encore « {role} ». La revue sert à "
        "trouver cet accès et à le retirer, pas seulement à le consigner."
    )

    entree = par_nom[porteur]
    roles_lus = (
        entree.get("roles") or entree.get("rôles")
        or entree.get("realmRoles") or []
    )
    assert role not in roles_lus, (
        f"La revue montre « {porteur} » avec « {role} ». Elle a été écrite "
        "AVANT le retrait : une revue qui décrit un état révolu est pire "
        "qu'aucune revue."
    )
