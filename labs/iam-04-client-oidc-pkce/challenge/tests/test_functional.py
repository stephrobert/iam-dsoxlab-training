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

from conftest import lab_host, lab_target_host, message

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
    assert fichier.exists, message(
        en=f"{IDENTIFIANTS} is missing. The lab's setup did not run, or its "
        "staging script failed: the trace is in "
        "/var/log/dsoxlab-prepare.log on the machine.",
        fr=f"{IDENTIFIANTS} est absent. Le setup du lab n'a pas tourné, ou son "
        "script de mise en situation a échoué : la trace est dans "
        "/var/log/dsoxlab-prepare.log sur la machine.",
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
    assert jeton, message(
        en="No administration token could be obtained. Is Keycloak answering "
        f"on {KEYCLOAK}, and is the base installed? (rc={res.rc}, "
        f"stderr={res.stderr.strip()[:200]})",
        fr="Aucun jeton d'administration n'a pu être obtenu. Keycloak répond-il "
        f"sur {KEYCLOAK}, et le socle est-il installé ? (rc={res.rc}, "
        f"stderr={res.stderr.strip()[:200]})",
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
            message(
            en="The administration API returned no JSON for the list of "
            f"clients: {res.stdout[:300]}",
            fr="L'API d'administration n'a pas rendu de JSON pour la liste des "
            f"clients : {res.stdout[:300]}",
        )
        )
    assert trouves, message(
        en=f"No client \"{CLIENT}\" in the realm \"{REALM}\". That is the challenge's "
        "first move: the application must have an identity with the "
        "provider.",
        fr=f"Aucun client « {CLIENT} » dans le realm « {REALM} ». C'est le premier "
        "geste du challenge : l'application doit avoir une identité auprès du "
        "fournisseur.",
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
    assert res.rc != 2, message(
        en="The journey tool could not measure, which is not a failure of "
        f"the integration: {res.stderr.strip()[:400]}",
        fr="L'outil de parcours n'a pas pu mesurer, ce qui n'est pas un échec de "
        f"l'intégration : {res.stderr.strip()[:400]}",
    )
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        pytest.fail(
            message(
            en=f"The journey returned nothing usable (rc={res.rc}): "
            f"{(res.stdout + res.stderr)[:400]}",
            fr=f"Le parcours n'a rien rendu d'exploitable (rc={res.rc}) : "
            f"{(res.stdout + res.stderr)[:400]}",
        )
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
        assert declarees, message(
            en="The client declares no redirect URI.",
            fr="Le client ne déclare aucune URI de redirection.",
        )
        options = f"{options} --redirect-uri {declarees[0]!r}"
    res = hote.run(
        f"python3 {OUTILS}/navigateur.py --realm {REALM} --client {CLIENT} "
        f"--utilisateur {identifiants['UTILISATEUR']} "
        f"--mot-de-passe {identifiants['MOT_DE_PASSE']!r} {options}"
    )
    assert res.rc != 2, message(
        en="The flow tool could not measure, which is not a refusal from "
        f"Keycloak: {res.stderr.strip()[:400]}",
        fr="L'outil de flux n'a pas pu mesurer, ce qui n'est pas un refus de "
        f"Keycloak : {res.stderr.strip()[:400]}",
    )
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        pytest.fail(
            message(
            en=f"The flow returned nothing usable (rc={res.rc}): "
            f"{(res.stdout + res.stderr)[:400]}",
            fr=f"Le flux n'a rien rendu d'exploitable (rc={res.rc}) : "
            f"{(res.stdout + res.stderr)[:400]}",
        )
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

    assert client.get("enabled") is True, message(
        en=f"The client \"{CLIENT}\" exists but it is disabled: no flow will "
        "start.",
        fr=f"Le client « {CLIENT} » existe mais il est désactivé : aucun flux ne "
        "partira.",
    )
    assert client.get("publicClient") is True, message(
        en=f"The client \"{CLIENT}\" is confidential. An application the "
        "user runs (browser, mobile, workstation) can keep no "
        "secret: it is public, and that is precisely why PKCE exists.",
        fr=f"Le client « {CLIENT} » est confidentiel. Une application que "
        "l'utilisateur exécute (navigateur, mobile, poste de travail) ne peut "
        "garder aucun secret : elle est publique, et c'est précisément pour "
        "cela que PKCE existe.",
    )
    assert not client.get("secret"), message(
        en="The client carries a secret. A secret in a public application "
        "is readable by anyone who installs it, and it then gives a false "
        "sense of protection.",
        fr="Le client porte un secret. Un secret dans une application publique "
        "est lisible par quiconque l'installe, et il donne alors un faux "
        "sentiment de protection.",
    )


def test_seul_le_flux_standard_est_ouvert(idp):
    """Les trois autres octrois doivent être fermés, un par un.

    Vert avant le travail ? Non : le client n'existe pas. Et un client créé
    sans y penser arrive avec l'octroi direct ACTIVÉ par défaut, ce qui est
    exactement le réglage que ce test refuse.
    """
    client = _client_declare(idp)

    assert client.get("standardFlowEnabled") is True, message(
        en="The standard flow is closed: that is the authorization code flow, "
        "the only one this lab asks for.",
        fr="Le flux standard est fermé : c'est pourtant le flux de code "
        "d'autorisation, le seul que ce lab demande.",
    )
    assert client.get("implicitFlowEnabled") is False, message(
        en="The implicit flow is open. It returns the token in the URL, hence in "
        "the browser's history and in the logs of intermediate "
        "servers. RFC 9700 forbids it.",
        fr="Le flux implicite est ouvert. Il rend le jeton dans l'URL, donc dans "
        "l'historique du navigateur et dans les journaux des serveurs "
        "intermédiaires. La RFC 9700 le proscrit.",
    )
    assert client.get("directAccessGrantsEnabled") is False, message(
        en="The password grant is open. It makes the user's password pass "
        "THROUGH the application, which the whole authorization code flow "
        "exists to avoid. It is the default setting of a "
        "client created without thinking, so the one to close by hand.",
        fr="L'octroi par mot de passe est ouvert. Il fait passer le mot de passe "
        "de l'utilisateur PAR l'application, ce que tout le flux de code "
        "d'autorisation existe pour éviter. C'est le réglage par défaut d'un "
        "client créé sans y penser, donc celui qu'il faut fermer à la main.",
    )
    assert client.get("serviceAccountsEnabled") is False, message(
        en="The service account is open on a public client, which makes no "
        "sense: with no secret, anyone could use it.",
        fr="Le compte de service est ouvert sur un client public, ce qui n'a pas "
        "de sens : sans secret, n'importe qui pourrait s'en servir.",
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

    assert methode == "S256", message(
        en="The client does not require PKCE with S256 (value read: "
        f"{methode!r}). With `plain`, the verifier travels in clear and PKCE "
        "protects nothing any more; absent, an intercepted code is enough to obtain "
        "a token.",
        fr="Le client n'exige pas PKCE en S256 (valeur lue : "
        f"{methode!r}). En `plain`, le vérifieur voyage en clair et PKCE ne "
        "protège plus de rien ; absent, un code intercepté suffit à obtenir "
        "un jeton.",
    )

    refuse = _flux_direct(idp, "--pkce --sans-verifier")
    assert refuse.get("echange_http") == 400, message(
        en="Keycloak accepted a code exchange WITHOUT a PKCE verifier "
        f"(HTTP {refuse.get('echange_http')}). The attribute is therefore set without "
        f"effect. Server's answer: {str(refuse.get('jetons'))[:300]}",
        fr="Keycloak a accepté un échange de code SANS vérifieur PKCE "
        f"(HTTP {refuse.get('echange_http')}). L'attribut est donc posé sans "
        f"effet. Réponse du serveur : {str(refuse.get('jetons'))[:300]}",
    )
    erreur = (refuse.get("jetons") or {}).get("error")
    assert erreur == "invalid_grant", message(
        en=f"The refusal is not the expected one: {erreur!r}. Measured on Keycloak "
        "26.8.1, an exchange with no verifier returns `invalid_grant` with the "
        "description \"PKCE code verifier not specified\".",
        fr=f"Le refus n'est pas celui attendu : {erreur!r}. Mesuré sur Keycloak "
        "26.8.1, un échange sans vérifieur rend `invalid_grant` avec la "
        "description « PKCE code verifier not specified ».",
    )

    accepte = _flux_direct(idp, "--pkce")
    assert accepte.get("echange_http") == 200, message(
        en="The same flow WITH a verifier fails too "
        f"(HTTP {accepte.get('echange_http')}). The client therefore refuses "
        f"everybody: {str(accepte.get('jetons'))[:300]}",
        fr="Le même flux AVEC vérifieur échoue aussi "
        f"(HTTP {accepte.get('echange_http')}). Le client refuse donc tout le "
        f"monde : {str(accepte.get('jetons'))[:300]}",
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

    assert uris, message(
        en="The client declares no redirect URI.",
        fr="Le client ne déclare aucune URI de redirection.",
    )
    fautives = [u for u in uris if "*" in u]
    assert not fautives, message(
        en=f"Wildcard redirect URIs: {fautives}. Keycloak accepts the "
        "`*` character, and that is precisely what must not be asked of "
        "it: the URI must be exact, path included.",
        fr=f"URI de redirection en joker : {fautives}. Keycloak accepte le "
        "caractère `*`, et c'est précisément ce qu'il ne faut pas lui "
        "demander : l'URI doit être exacte, chemin compris.",
    )

    origines = client.get("webOrigins") or []
    assert "*" not in origines, message(
        en="The web origins contain `*`, which allows any site "
        "to call the provider from the user's browser.",
        fr="Les origines web contiennent `*`, ce qui autorise n'importe quel site "
        "à appeler le fournisseur depuis le navigateur de l'utilisateur.",
    )

    refuse = _flux_direct(
        idp, "--pkce --redirect-uri http://127.0.0.1:9999/vole"
    )
    refus = refuse.get("refus_a_l_autorisation") or ""
    assert "redirect_uri" in refus, message(
        en="Keycloak did not refuse an undeclared redirect URI "
        f"(answer: {json.dumps(refuse, ensure_ascii=False)[:300]}). A URI "
        "declared too broadly lets an attacker's address through.",
        fr="Keycloak n'a pas refusé une URI de redirection non déclarée "
        f"(réponse : {json.dumps(refuse, ensure_ascii=False)[:300]}). Une URI "
        "déclarée trop largement laisse passer l'adresse d'un attaquant.",
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
    assert etat.rc == 0 and etat.stdout.strip(), message(
        en=f"The witness application does not answer on port {PORT_TEMOIN}. It "
        f"is started from {APPLI} with its virtual environment's interpreter, "
        "and the challenge says how.",
        fr=f"L'application témoin ne répond pas sur le port {PORT_TEMOIN}. Elle "
        f"se lance depuis {APPLI} avec l'interpréteur de son environnement "
        "virtuel, et le challenge dit comment.",
    )
    lu = json.loads(etat.stdout)
    assert lu.get("configuration_lue") is True, message(
        en="The application runs but does not read its configuration: "
        f"{lu.get('configuration_erreur')}. It expects a "
        f"`configuration.json` file in {APPLI}.",
        fr="L'application tourne mais ne lit pas sa configuration : "
        f"{lu.get('configuration_erreur')}. Elle attend un fichier "
        f"`configuration.json` dans {APPLI}.",
    )

    resultat = _parcours(
        idp, utilisateur, identifiants["MOT_DE_PASSE"], attendu
    )

    assert resultat.get("connexion_posee") is True, message(
        en="The journey never met the login form. "
        "The application therefore did not take the user to the provider: "
        f"it stopped on {resultat.get('arrivee')}.",
        fr="Le parcours n'a jamais rencontré le formulaire de connexion. "
        "L'application n'a donc pas emmené l'utilisateur chez le fournisseur : "
        f"il s'est arrêté sur {resultat.get('arrivee')}.",
    )
    assert resultat.get("texte_trouve") is True, message(
        en=f"The landing page does not carry \"{attendu}\". The journey "
        f"ended on {resultat.get('arrivee')} (HTTP {resultat.get('http')}) "
        f"with: {str(resultat.get('texte'))[:300]}",
        fr=f"La page d'arrivée ne porte pas « {attendu} ». Le parcours s'est "
        f"terminé sur {resultat.get('arrivee')} (HTTP {resultat.get('http')}) "
        f"avec : {str(resultat.get('texte'))[:300]}",
    )

    apres = json.loads(
        idp.run(f"curl -sS --max-time 10 http://127.0.0.1:{PORT_TEMOIN}/etat").stdout
    )
    assert apres.get("connecte") is True and apres.get("utilisateur") == utilisateur, message(
        en="The application shows the page but its state does not say that it "
        f"validated the ID token: {json.dumps(apres, ensure_ascii=False)[:300]}",
        fr="L'application affiche la page mais son état ne dit pas qu'elle a "
        f"validé l'ID token : {json.dumps(apres, ensure_ascii=False)[:300]}",
    )
    validations = apres.get("validations") or []
    assert validations and validations[-1].get("ok") is True, message(
        en="The last ID token validation failed: "
        f"{json.dumps(validations[-1:], ensure_ascii=False)[:300]}",
        fr="La dernière validation d'ID token a échoué : "
        f"{json.dumps(validations[-1:], ensure_ascii=False)[:300]}",
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
    assert "id_token" in jetons, message(
        en="The flow returned no ID token. Is the `openid` scope granted to the "
        f"client? Answer: {str(jetons)[:300]}",
        fr="Le flux n'a rendu aucun ID token. Le scope `openid` est-il accordé au "
        f"client ? Réponse : {str(jetons)[:300]}",
    )

    revendications = _revendications(jetons["id_token"])

    assert revendications.get("iss") == f"{KEYCLOAK}/realms/{REALM}", message(
        en=f"The ID token's issuer is {revendications.get('iss')!r} instead "
        f"of {KEYCLOAK}/realms/{REALM}. The client is not declared in the "
        "lab's realm.",
        fr=f"L'émetteur de l'ID token est {revendications.get('iss')!r} au lieu "
        f"de {KEYCLOAK}/realms/{REALM}. Le client n'est pas déclaré dans le "
        "realm du lab.",
    )
    assert revendications.get("aud") == CLIENT, message(
        en=f"The ID token's audience is {revendications.get('aud')!r} instead "
        f"of {CLIENT!r}. An application that does not check `aud` accepts a "
        "token issued for another.",
        fr=f"L'audience de l'ID token est {revendications.get('aud')!r} au lieu "
        f"de {CLIENT!r}. Une application qui ne vérifie pas `aud` accepte un "
        "jeton délivré pour une autre.",
    )
    assert revendications.get("nonce") == flux.get("nonce_envoye"), message(
        en="The ID token's nonce does not match the one sent "
        f"({revendications.get('nonce')!r} against "
        f"{flux.get('nonce_envoye')!r}). Without that link, the ID token of another "
        "session could be replayed.",
        fr="Le nonce de l'ID token ne correspond pas à celui envoyé "
        f"({revendications.get('nonce')!r} contre "
        f"{flux.get('nonce_envoye')!r}). Sans ce lien, l'ID token d'une autre "
        "connexion pourrait être rejoué.",
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
    assert res.rc == 0 and res.stdout.strip(), message(
        en=f"The witness application does not answer on port {PORT_TEMOIN}.",
        fr=f"L'application témoin ne répond pas sur le port {PORT_TEMOIN}.",
    )
    lu = json.loads(res.stdout)

    assert lu.get("issuer") == f"{KEYCLOAK}/realms/{REALM}", message(
        en=f"The application talks to {lu.get('issuer')!r}. It must talk "
        f"to the realm \"{REALM}\": a realm serves one population, and the one of "
        "the server's administrators is not the one of an application's "
        "users.",
        fr=f"L'application s'adresse à {lu.get('issuer')!r}. Elle doit s'adresser "
        f"au realm « {REALM} » : un realm sert une population, et celui des "
        "administrateurs du serveur n'est pas celui des utilisateurs d'une "
        "application.",
    )
    assert lu.get("client_id") == CLIENT, message(
        en=f"The application presents itself as {lu.get('client_id')!r} instead of "
        f"{CLIENT!r}.",
        fr=f"L'application se présente sous {lu.get('client_id')!r} au lieu de "
        f"{CLIENT!r}.",
    )
