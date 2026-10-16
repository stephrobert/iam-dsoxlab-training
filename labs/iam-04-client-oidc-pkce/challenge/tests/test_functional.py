"""Ce que le fournisseur impose vraiment, et ce que l'application obtient.

Aucun test n'ouvre la configuration de l'apprenant. Ils interrogent Keycloak par
son API d'administration, et surtout ils JOUENT le flux : un client correctement
déclaré se reconnaît à ce qu'il refuse, pas à ce que sa fiche annonce.

Trois refus sont mesurés pour de vrai, parce qu'un attribut peut être posé sans
effet :

- un échange de code sans `code_verifier` doit être refusé, PKCE étant exigé ;
- une URI de redirection non déclarée doit être refusée à l'autorisation ;
- l'ID token doit porter l'émetteur du realm du lab et l'audience du client.

Vert avant le travail ? Non, pour tous : le setup retire le client s'il existe,
et l'application témoin n'a pas de configuration. Mesuré le 2026-10-16.
"""

from __future__ import annotations

import base64
import json

import pytest

from conftest import lab_host, lab_target_host

# L'hôte RÉELLEMENT testé. `dsoxlab check --target` peut en imposer un autre,
# et coder le nom en dur ferait tester la cible par défaut en prétendant tester
# celle qu'on a demandée.
CIBLE = lab_target_host("idp.lab")

KEYCLOAK = "http://127.0.0.1:8080"
REALM = "formation"
CLIENT = "appli-notes"
PORT_TEMOIN = 9080
OUTILS = "/opt/iam-lab/outils"
APPLI = "/opt/iam-lab/appli-temoin"
IDENTIFIANTS = "/opt/iam-lab/identifiants-lab.txt"
SECRETS_DU_SOCLE = "/opt/socle-iam/secrets.yml"


@pytest.fixture(scope="module")
def idp():
    """La machine du lab.

    `lab_host` est une fonction du conftest, pas une fixture : chaque lab bâtit
    la sienne, ce qui permet à un lab multi-hôtes d'en avoir plusieurs.
    """
    return lab_host(CIBLE)


# ── Outils de lecture de l'état ──────────────────────────────────────────────


def _identifiants(hote) -> dict[str, str]:
    """Le compte de test, tel que le setup l'a posé."""
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
    """Un jeton d'administration, obtenu avec le compte du socle.

    Les tests lisent les secrets du socle, qui vivent sur la machine et sont
    tirés au hasard à son installation. Rien de cela n'est versionné.
    """
    # SANS `set -o pipefail`, et ce n'est pas un oubli.
    #
    # Mesuré le 2026-10-16 : testinfra exécute par `/bin/sh`, qui est `dash`
    # sur Ubuntu, et répond « set: Illegal option -o pipefail ». Les tests
    # échouaient alors tous sur « aucun jeton d'administration », ce qui
    # désignait Keycloak alors que Keycloak allait très bien.
    #
    # Rien n'est perdu : le résultat est vérifié juste après, ce qui vaut mieux
    # qu'un code de retour de tube.
    res = hote.run(
        f"u=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME:' {SECRETS_DU_SOCLE} | cut -d'\"' -f2); "
        f"p=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD:' {SECRETS_DU_SOCLE} | cut -d'\"' -f2); "
        f"curl -sS --max-time 20 -X POST {KEYCLOAK}/realms/master/protocol/openid-connect/token "
        "-d grant_type=password -d client_id=admin-cli "
        '-d "username=$u" -d "password=$p" | jq -r \'.access_token // empty\''
    )
    jeton = res.stdout.strip()
    assert jeton, (
        "Aucun jeton d'administration n'a pu être obtenu. Keycloak répond-il "
        f"sur {KEYCLOAK}, et le socle est-il installé ? (rc={res.rc}, "
        f"stderr={res.stderr.strip()[:200]})"
    )
    return jeton


def _client_declare(hote) -> dict:
    """La déclaration du client, vue par l'API d'administration."""
    jeton = _jeton_admin(hote)
    res = hote.run(
        f"curl -sS --max-time 20 '{KEYCLOAK}/admin/realms/{REALM}/clients"
        f"?clientId={CLIENT}' -H 'Authorization: Bearer {jeton}'"
    )
    try:
        trouves = json.loads(res.stdout or "[]")
    except json.JSONDecodeError:
        pytest.fail(
            "L'API d'administration n'a pas rendu de JSON pour la liste des "
            f"clients : {res.stdout[:300]}"
        )
    assert trouves, (
        f"Aucun client « {CLIENT} » dans le realm « {REALM} ». C'est le premier "
        "geste du challenge : l'application doit avoir une identité auprès du "
        "fournisseur."
    )
    return trouves[0]


def _parcours(hote, utilisateur: str, mot_de_passe: str, attendu: str) -> dict:
    """Le parcours d'un navigateur, de l'application jusqu'au retour.

    L'outil sort en 2 quand il n'a pas pu mesurer, ce qui ne doit JAMAIS être
    confondu avec « l'intégration est cassée ».
    """
    res = hote.run(
        f"python3 {OUTILS}/parcours.py "
        f"--depart http://127.0.0.1:{PORT_TEMOIN}/connexion "
        f"--utilisateur {utilisateur} --mot-de-passe {mot_de_passe!r} "
        f"--attendre-texte {attendu!r}"
    )
    assert res.rc != 2, (
        "L'outil de parcours n'a pas pu mesurer, ce qui n'est pas un échec de "
        f"l'intégration : {res.stderr.strip()[:400]}"
    )
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        pytest.fail(
            f"Le parcours n'a rien rendu d'exploitable (rc={res.rc}) : "
            f"{(res.stdout + res.stderr)[:400]}"
        )


def _flux_direct(hote, options: str) -> dict:
    """Un flux de code d'autorisation joué directement contre Keycloak.

    L'URI de redirection est celle que L'APPRENANT A DÉCLARÉE, lue sur le
    client, sauf quand `options` en impose une autre pour éprouver un refus.
    La coder en dur ferait échouer le flux chez quiconque a choisi un autre
    hôte, ce que le challenge autorise.

    Mesuré le 2026-10-16 : sans `--redirect-uri`, `navigateur.py` sort en 2 par
    argparse, et le test concluait « l'outil n'a pas pu mesurer » alors que
    c'était son appel qui était incomplet.
    """
    identifiants = _identifiants(hote)
    if "--redirect-uri" not in options:
        declarees = _client_declare(hote).get("redirectUris") or []
        assert declarees, "Le client ne déclare aucune URI de redirection."
        options = f"{options} --redirect-uri {declarees[0]!r}"
    res = hote.run(
        f"python3 {OUTILS}/navigateur.py --realm {REALM} --client {CLIENT} "
        f"--utilisateur {identifiants['UTILISATEUR']} "
        f"--mot-de-passe {identifiants['MOT_DE_PASSE']!r} {options}"
    )
    assert res.rc != 2, (
        "L'outil de flux n'a pas pu mesurer, ce qui n'est pas un refus de "
        f"Keycloak : {res.stderr.strip()[:400]}"
    )
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        pytest.fail(
            f"Le flux n'a rien rendu d'exploitable (rc={res.rc}) : "
            f"{(res.stdout + res.stderr)[:400]}"
        )


def _revendications(jeton: str) -> dict:
    """Les revendications d'un JWT, SANS vérifier sa signature.

    C'est volontaire et sans danger ici : le jeton vient d'être obtenu du
    serveur par le test lui-même. On lit ce qu'il contient, on ne lui accorde
    aucune confiance.
    """
    charge = jeton.split(".")[1]
    charge += "=" * (-len(charge) % 4)
    return json.loads(base64.urlsafe_b64decode(charge))


# ── Les tests ────────────────────────────────────────────────────────────────


def test_le_client_est_declare_et_public(idp):
    """Un client public, donc sans secret : l'application tourne chez l'usager.

    Vert avant le travail ? Non : le setup retire le client s'il en trouve un.
    """
    client = _client_declare(idp)

    assert client.get("enabled") is True, (
        f"Le client « {CLIENT} » existe mais il est désactivé : aucun flux ne "
        "partira."
    )
    assert client.get("publicClient") is True, (
        f"Le client « {CLIENT} » est confidentiel. Une application que "
        "l'utilisateur exécute (navigateur, mobile, poste de travail) ne peut "
        "garder aucun secret : elle est publique, et c'est précisément pour "
        "cela que PKCE existe."
    )
    assert not client.get("secret"), (
        "Le client porte un secret. Un secret dans une application publique "
        "est lisible par quiconque l'installe, et il donne alors un faux "
        "sentiment de protection."
    )


def test_seul_le_flux_standard_est_ouvert(idp):
    """Les trois autres octrois doivent être fermés, un par un.

    Vert avant le travail ? Non : le client n'existe pas. Et un client créé
    sans y penser arrive avec l'octroi direct ACTIVÉ par défaut, ce qui est
    exactement le réglage que ce test refuse.
    """
    client = _client_declare(idp)

    assert client.get("standardFlowEnabled") is True, (
        "Le flux standard est fermé : c'est pourtant le flux de code "
        "d'autorisation, le seul que ce lab demande."
    )
    assert client.get("implicitFlowEnabled") is False, (
        "Le flux implicite est ouvert. Il rend le jeton dans l'URL, donc dans "
        "l'historique du navigateur et dans les journaux des serveurs "
        "intermédiaires. La RFC 9700 le proscrit."
    )
    assert client.get("directAccessGrantsEnabled") is False, (
        "L'octroi par mot de passe est ouvert. Il fait passer le mot de passe "
        "de l'utilisateur PAR l'application, ce que tout le flux de code "
        "d'autorisation existe pour éviter. C'est le réglage par défaut d'un "
        "client créé sans y penser, donc celui qu'il faut fermer à la main."
    )
    assert client.get("serviceAccountsEnabled") is False, (
        "Le compte de service est ouvert sur un client public, ce qui n'a pas "
        "de sens : sans secret, n'importe qui pourrait s'en servir."
    )


def test_pkce_est_exige_et_le_serveur_le_prouve(idp):
    """L'attribut, PUIS le refus réel. Le premier sans le second ne vaut rien.

    Vert avant le travail ? Non : sans client, il n'y a pas de flux à jouer.

    Un attribut peut être posé sur un client sans que le serveur l'applique,
    par exemple parce qu'il est écrit au mauvais endroit. Le seul contrôle qui
    tienne est de demander un jeton sans `code_verifier` et de vérifier que
    Keycloak refuse.
    """
    client = _client_declare(idp)
    methode = (client.get("attributes") or {}).get("pkce.code.challenge.method")

    assert methode == "S256", (
        "Le client n'exige pas PKCE en S256 (valeur lue : "
        f"{methode!r}). En `plain`, le vérifieur voyage en clair et PKCE ne "
        "protège plus de rien ; absent, un code intercepté suffit à obtenir "
        "un jeton."
    )

    refuse = _flux_direct(idp, "--pkce --sans-verifier")
    assert refuse.get("echange_http") == 400, (
        "Keycloak a accepté un échange de code SANS vérifieur PKCE "
        f"(HTTP {refuse.get('echange_http')}). L'attribut est donc posé sans "
        f"effet. Réponse du serveur : {str(refuse.get('jetons'))[:300]}"
    )
    erreur = (refuse.get("jetons") or {}).get("error")
    assert erreur == "invalid_grant", (
        f"Le refus n'est pas celui attendu : {erreur!r}. Mesuré sur Keycloak "
        "26.8.1, un échange sans vérifieur rend `invalid_grant` avec la "
        "description « PKCE code verifier not specified »."
    )

    accepte = _flux_direct(idp, "--pkce")
    assert accepte.get("echange_http") == 200, (
        "Le même flux AVEC vérifieur échoue aussi "
        f"(HTTP {accepte.get('echange_http')}). Le client refuse donc tout le "
        f"monde : {str(accepte.get('jetons'))[:300]}"
    )


def test_aucune_uri_de_redirection_en_joker(idp):
    """Les URI déclarées, puis le refus d'une URI qui ne l'est pas.

    Vert avant le travail ? Non : sans client, rien à lire.

    Une URI en joker laisse un attaquant se faire renvoyer le code
    d'autorisation sur une adresse qu'il contrôle. C'est la faille la plus
    courante des intégrations OIDC, et elle ne se voit jamais à l'usage : le
    flux normal fonctionne parfaitement.
    """
    client = _client_declare(idp)
    uris = client.get("redirectUris") or []

    assert uris, "Le client ne déclare aucune URI de redirection."
    fautives = [u for u in uris if "*" in u]
    assert not fautives, (
        f"URI de redirection en joker : {fautives}. Keycloak accepte le "
        "caractère `*`, et c'est précisément ce qu'il ne faut pas lui "
        "demander : l'URI doit être exacte, chemin compris."
    )

    origines = client.get("webOrigins") or []
    assert "*" not in origines, (
        "Les origines web contiennent `*`, ce qui autorise n'importe quel site "
        "à appeler le fournisseur depuis le navigateur de l'utilisateur."
    )

    refuse = _flux_direct(
        idp, "--pkce --redirect-uri http://127.0.0.1:9999/vole"
    )
    message = refuse.get("refus_a_l_autorisation") or ""
    assert "redirect_uri" in message, (
        "Keycloak n'a pas refusé une URI de redirection non déclarée "
        f"(réponse : {json.dumps(refuse, ensure_ascii=False)[:300]}). Une URI "
        "déclarée trop largement laisse passer l'adresse d'un attaquant."
    )


def test_l_application_temoin_connecte_vraiment_l_utilisateur(idp):
    """Le parcours entier, comme un navigateur le ferait.

    Vert avant le travail ? Non : l'application n'a pas de configuration, et
    sans client elle n'aurait personne à qui s'adresser.

    C'est le test qui compte le plus. Tous les réglages précédents peuvent être
    justes sans que l'application fonctionne, par exemple si sa configuration
    pointe un autre realm. Ici l'utilisateur arrive sur la page, et son nom y
    est écrit.
    """
    identifiants = _identifiants(idp)
    utilisateur = identifiants["UTILISATEUR"]
    attendu = f"Connecté en tant que {utilisateur}"

    etat = idp.run(f"curl -sS --max-time 10 http://127.0.0.1:{PORT_TEMOIN}/etat")
    assert etat.rc == 0 and etat.stdout.strip(), (
        f"L'application témoin ne répond pas sur le port {PORT_TEMOIN}. Elle "
        f"se lance depuis {APPLI} avec l'interpréteur de son environnement "
        "virtuel, et le challenge dit comment."
    )
    lu = json.loads(etat.stdout)
    assert lu.get("configuration_lue") is True, (
        "L'application tourne mais ne lit pas sa configuration : "
        f"{lu.get('configuration_erreur')}. Elle attend un fichier "
        f"`configuration.json` dans {APPLI}."
    )

    resultat = _parcours(
        idp, utilisateur, identifiants["MOT_DE_PASSE"], attendu
    )

    assert resultat.get("connexion_posee") is True, (
        "Le parcours n'a jamais rencontré le formulaire de connexion. "
        "L'application n'a donc pas emmené l'utilisateur chez le fournisseur : "
        f"il s'est arrêté sur {resultat.get('arrivee')}."
    )
    assert resultat.get("texte_trouve") is True, (
        f"La page d'arrivée ne porte pas « {attendu} ». Le parcours s'est "
        f"terminé sur {resultat.get('arrivee')} (HTTP {resultat.get('http')}) "
        f"avec : {str(resultat.get('texte'))[:300]}"
    )

    apres = json.loads(
        idp.run(f"curl -sS --max-time 10 http://127.0.0.1:{PORT_TEMOIN}/etat").stdout
    )
    assert apres.get("connecte") is True and apres.get("utilisateur") == utilisateur, (
        "L'application affiche la page mais son état ne dit pas qu'elle a "
        f"validé l'ID token : {json.dumps(apres, ensure_ascii=False)[:300]}"
    )
    validations = apres.get("validations") or []
    assert validations and validations[-1].get("ok") is True, (
        "La dernière validation d'ID token a échoué : "
        f"{json.dumps(validations[-1:], ensure_ascii=False)[:300]}"
    )


def test_l_id_token_porte_l_emetteur_et_l_audience_attendus(idp):
    """Les trois revendications qui empêchent un jeton d'être réutilisé ailleurs.

    Vert avant le travail ? Non : il n'y a pas de jeton à lire sans client.

    Un jeton parfaitement signé par le même serveur, mais émis par un autre
    realm ou destiné à une autre application, est un jeton qu'il faut refuser.
    C'est `iss` et `aud` qui le disent, et `nonce` qui empêche de rejouer celui
    d'une autre connexion.
    """
    flux = _flux_direct(idp, "--pkce")
    jetons = flux.get("jetons") or {}
    assert "id_token" in jetons, (
        "Le flux n'a rendu aucun ID token. Le scope `openid` est-il accordé au "
        f"client ? Réponse : {str(jetons)[:300]}"
    )

    revendications = _revendications(jetons["id_token"])

    assert revendications.get("iss") == f"{KEYCLOAK}/realms/{REALM}", (
        f"L'émetteur de l'ID token est {revendications.get('iss')!r} au lieu "
        f"de {KEYCLOAK}/realms/{REALM}. Le client n'est pas déclaré dans le "
        "realm du lab."
    )
    assert revendications.get("aud") == CLIENT, (
        f"L'audience de l'ID token est {revendications.get('aud')!r} au lieu "
        f"de {CLIENT!r}. Une application qui ne vérifie pas `aud` accepte un "
        "jeton délivré pour une autre."
    )
    assert revendications.get("nonce") == flux.get("nonce_envoye"), (
        "Le nonce de l'ID token ne correspond pas à celui envoyé "
        f"({revendications.get('nonce')!r} contre "
        f"{flux.get('nonce_envoye')!r}). Sans ce lien, l'ID token d'une autre "
        "connexion pourrait être rejoué."
    )


def test_la_configuration_du_temoin_pointe_le_realm_du_lab(idp):
    """L'application doit s'adresser au bon fournisseur, pas à n'importe lequel.

    Vert avant le travail ? Non : `configuration.json` est retiré par le setup.

    Ce contrôle semble redondant avec le parcours, et il ne l'est pas : une
    configuration qui pointerait le realm `master` ferait entrer un
    administrateur du serveur dans une application de notes. Le flux
    réussirait, et le test du parcours serait vert.
    """
    res = idp.run(f"curl -sS --max-time 10 http://127.0.0.1:{PORT_TEMOIN}/etat")
    assert res.rc == 0 and res.stdout.strip(), (
        f"L'application témoin ne répond pas sur le port {PORT_TEMOIN}."
    )
    lu = json.loads(res.stdout)

    assert lu.get("issuer") == f"{KEYCLOAK}/realms/{REALM}", (
        f"L'application s'adresse à {lu.get('issuer')!r}. Elle doit s'adresser "
        f"au realm « {REALM} » : un realm sert une population, et celui des "
        "administrateurs du serveur n'est pas celui des utilisateurs d'une "
        "application."
    )
    assert lu.get("client_id") == CLIENT, (
        f"L'application se présente sous {lu.get('client_id')!r} au lieu de "
        f"{CLIENT!r}."
    )
