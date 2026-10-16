"""L'intégration remarche, et aucun raccourci n'a été pris pour y arriver.

Ce lab est le seul du catalogue dont le setup CASSE quelque chose. Il tire une
panne au hasard parmi cinq, toutes mesurées le 2026-10-16 :

    URI de redirection fautive   « Invalid parameter: redirect_uri »
    issuer fautif côté appli     « Client not found » sur le MAUVAIS realm
    client confidentiel          « unauthorized_client »
    client désactivé             « Client disabled. »
    flux de code fermé           « Standard flow is disabled for the client »

LES TESTS NE CHERCHENT PAS À SAVOIR LAQUELLE

Ils vérifient que l'état final est CORRECT, en entier. C'est équivalent et plus
honnête : une réparation qui remet le bon état répare quelle que soit la panne,
et aucun test ne peut être satisfait par une correction qui en cacherait une
autre.

LA MOITIÉ DE LA NOTE PORTE SUR CE QUI N'A PAS ÉTÉ FAIT

Chacune de ces cinq pannes se contourne. On peut élargir une URI en joker,
passer le client en confidentiel avec un secret écrit dans l'application,
désactiver PKCE, ouvrir l'octroi par mot de passe. Tout cela fait remarcher
l'application, et chacun de ces gestes ouvre une faille que personne ne
remarquera. Les tests les refusent un par un.
"""

from __future__ import annotations

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
SECRETS_DU_SOCLE = "/opt/socle-iam/.env"


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
    """Sans `set -o pipefail` : testinfra exécute par `/bin/sh`, donc `dash`."""
    res = hote.run(
        f"u=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME=' {SECRETS_DU_SOCLE} | cut -d= -f2-); "
        f"p=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD=' {SECRETS_DU_SOCLE} | cut -d= -f2-); "
        f"curl -sS --max-time 20 -X POST {KEYCLOAK}/realms/master/protocol/openid-connect/token "
        "-d grant_type=password -d client_id=admin-cli "
        '-d "username=$u" -d "password=$p" | jq -r \'.access_token // empty\''
    )
    jeton = res.stdout.strip()
    assert jeton, message(
        en="No administration token could be obtained. Is Keycloak answering "
        f"on {KEYCLOAK}, and is the base installed? (rc={res.rc})",
        fr="Aucun jeton d'administration n'a pu être obtenu. Keycloak répond-il "
        f"sur {KEYCLOAK}, et le socle est-il installé ? (rc={res.rc})",
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
            message(
            en=f"The administration API returned no JSON for {chemin}: "
            f"{res.stdout[:300]}",
            fr=f"L'API d'administration n'a pas rendu de JSON pour {chemin} : "
            f"{res.stdout[:300]}",
        )
        )


def _client_declare(hote) -> dict:
    trouves = _api(hote, f"realms/{REALM}/clients?clientId={CLIENT}") or []
    assert trouves, message(
        en=f"No client \"{CLIENT}\" in the realm \"{REALM}\". It existed at the "
        "start: did you delete it rather than fix it?",
        fr=f"Aucun client « {CLIENT} » dans le realm « {REALM} ». Il existait au "
        "départ : l'avez-vous supprimé plutôt que corrigé ?",
    )
    return trouves[0]


def _attribut(client: dict, clef: str) -> str:
    return (client.get("attributes") or {}).get(clef, "")


def _etat_temoin(hote) -> dict:
    res = hote.run(f"curl -sS --max-time 10 http://127.0.0.1:{PORT_TEMOIN}/etat")
    assert res.rc == 0 and res.stdout.strip(), message(
        en=f"The witness application does not answer on port {PORT_TEMOIN}. Its "
        f"log is in {APPLI}/temoin.log.",
        fr=f"L'application témoin ne répond pas sur le port {PORT_TEMOIN}. Son "
        f"journal est dans {APPLI}/temoin.log.",
    )
    return json.loads(res.stdout)


def _parcours(hote) -> dict:
    identifiants = _identifiants(hote)
    attendu = f"Connecté en tant que {identifiants['UTILISATEUR']}"
    hote.run(f"curl -sS --max-time 10 http://127.0.0.1:{PORT_TEMOIN}/deconnexion")
    res = hote.run(
        f"python3 {OUTILS}/parcours.py "
        f"--depart http://127.0.0.1:{PORT_TEMOIN}/connexion "
        f"--utilisateur {identifiants['UTILISATEUR']} "
        f"--mot-de-passe {identifiants['MOT_DE_PASSE']!r} "
        f"--attendre-texte {attendu!r} --tours 25"
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


# ── Les tests ────────────────────────────────────────────────────────────────


def test_l_application_se_reconnecte(idp):
    """L'objectif, et il ne suffit pas.

    Vert avant le travail ? Non : le setup vérifie lui-même que le parcours
    échoue, et refuse de poser la situation si l'intégration fonctionne.

    Ce test seul serait satisfait par n'importe quel contournement. Les cinq
    suivants existent pour cela.
    """
    resultat = _parcours(idp)

    assert resultat.get("texte_trouve") is True, message(
        en="The login still fails. The journey ended on "
        f"{resultat.get('arrivee')} (HTTP {resultat.get('http')}) with:\n"
        f"  {str(resultat.get('texte'))[:400]}\n\n"
        "Read that message: it almost always names the faulty setting. And "
        "look at the realm's events, which the setup enabled: "
        "`LOGIN_ERROR` carries an `error` field there that says the cause in one word.",
        fr="La connexion échoue toujours. Le parcours s'est terminé sur "
        f"{resultat.get('arrivee')} (HTTP {resultat.get('http')}) avec :\n"
        f"  {str(resultat.get('texte'))[:400]}\n\n"
        "Lisez ce message : il nomme presque toujours le paramètre fautif. Et "
        "regardez les événements du realm, que le setup a activés : "
        "`LOGIN_ERROR` y porte un champ `error` qui dit la cause en un mot.",
    )

    etat = _etat_temoin(idp)
    assert etat.get("connecte") is True, message(
        en="The application shows the page but its state does not say it "
        f"validated the ID token: {json.dumps(etat, ensure_ascii=False)[:300]}",
        fr="L'application affiche la page mais son état ne dit pas qu'elle a "
        f"validé l'ID token : {json.dumps(etat, ensure_ascii=False)[:300]}",
    )
    validations = etat.get("validations") or []
    assert validations and validations[-1].get("ok") is True, message(
        en="The last ID token validation failed: "
        f"{json.dumps(validations[-1:], ensure_ascii=False)[:300]}",
        fr="La dernière validation d'ID token a échoué : "
        f"{json.dumps(validations[-1:], ensure_ascii=False)[:300]}",
    )


def test_aucune_uri_de_redirection_n_a_ete_elargie(idp):
    """Le contournement le plus tentant, et le plus coûteux.

    Vert avant le travail ? Non : le test exige que le client existe, et une
    des pannes le désactive ou le supprime de fait du chemin.

    Une URI en joker fait disparaître l'erreur « Invalid parameter:
    redirect_uri » immédiatement, et laisse un attaquant se faire renvoyer le
    code d'autorisation sur une adresse qu'il contrôle. C'est la faille la plus
    courante des intégrations OIDC, et elle ne se voit jamais à l'usage.
    """
    client = _client_declare(idp)
    uris = client.get("redirectUris") or []

    assert uris, message(
        en="The client declares no redirect URI.",
        fr="Le client ne déclare aucune URI de redirection.",
    )
    fautives = [u for u in uris if "*" in u]
    assert not fautives, message(
        en=f"Wildcard redirect URIs: {fautives}. If that was the breakage, the "
        "right fix is the EXACT URI the application uses, not a pattern "
        "covering everything.",
        fr=f"URI de redirection en joker : {fautives}. Si c'était la panne, la "
        "bonne correction est l'URI EXACTE que l'application utilise, pas un "
        "motif qui couvre tout.",
    )

    origines = client.get("webOrigins") or []
    assert "*" not in origines, message(
        en="The web origins contain `*`, which allows any site to call the "
        "provider from the user's browser.",
        fr="Les origines web contiennent `*`, ce qui autorise n'importe quel site "
        "à appeler le fournisseur depuis le navigateur de l'utilisateur.",
    )

    attendu = f"http://127.0.0.1:{PORT_TEMOIN}/callback"
    assert attendu in uris, message(
        en=f"The application's exact URI ({attendu}) is not declared "
        f"(declared: {uris}). The application's return path is "
        "`/callback`, and it is not negotiable.",
        fr=f"L'URI exacte de l'application ({attendu}) n'est pas déclarée "
        f"(déclarées : {uris}). Le chemin de retour de l'application est "
        "`/callback`, et il n'est pas négociable.",
    )


def test_le_client_est_reste_public_et_sans_secret(idp):
    """Le deuxième contournement : donner un secret à une application publique.

    Vert avant le travail ? Non : une des pannes passe justement le client en
    confidentiel, et le test est alors rouge.

    Passer le client en confidentiel fait disparaître l'erreur
    « unauthorized_client », à condition d'écrire le secret dans
    l'application. Ce secret est alors lisible par quiconque installe cette
    application, et il donne un faux sentiment de protection : c'est
    exactement pour cela que PKCE existe.
    """
    client = _client_declare(idp)

    assert client.get("publicClient") is True, message(
        en="The client is confidential. An application the user runs can keep "
        "no secret: if that was the breakage, the fix is to make it public "
        "again, not to entrust it with a secret.",
        fr="Le client est confidentiel. Une application que l'utilisateur exécute "
        "ne peut garder aucun secret : si c'était la panne, la correction est "
        "de la remettre publique, pas de lui confier un secret.",
    )
    assert not client.get("secret"), message(
        en="The client carries a secret. In a public application, it is "
        "readable by all those who install it.",
        fr="Le client porte un secret. Dans une application publique, il est "
        "lisible par tous ceux qui l'installent.",
    )
    assert client.get("enabled") is True, message(
        en="The client is disabled. That may have been the breakage: the fix "
        "is to enable it again.",
        fr="Le client est désactivé. C'était peut-être la panne : la correction "
        "est de le réactiver.",
    )


def test_pkce_est_toujours_exige_et_le_serveur_le_prouve(idp):
    """Le troisième contournement : désactiver une protection pour avancer.

    Vert avant le travail ? Non : le test joue un flux complet, qui échoue tant
    que la panne est là.

    PKCE est ce qui empêche un code d'autorisation intercepté de servir à
    quelqu'un d'autre. Le désactiver fait disparaître toute une classe
    d'erreurs, et c'est le genre de geste qu'on fait un vendredi soir en se
    disant qu'on y reviendra.
    """
    client = _client_declare(idp)
    methode = _attribut(client, "pkce.code.challenge.method")

    assert methode == "S256", message(
        en=f"The client no longer requires PKCE with S256 (value read: {methode!r}). "
        "With `plain`, the verifier travels in clear; absent, an intercepted "
        "code is enough to obtain a token.",
        fr=f"Le client n'exige plus PKCE en S256 (valeur lue : {methode!r}). En "
        "`plain`, le vérifieur voyage en clair ; absent, un code intercepté "
        "suffit à obtenir un jeton.",
    )

    # Le refus réel, parce qu'un attribut peut être posé sans effet.
    identifiants = _identifiants(idp)
    res = idp.run(
        f"python3 {OUTILS}/navigateur.py --realm {REALM} --client {CLIENT} "
        f"--redirect-uri http://127.0.0.1:{PORT_TEMOIN}/callback "
        f"--utilisateur {identifiants['UTILISATEUR']} "
        f"--mot-de-passe {identifiants['MOT_DE_PASSE']!r} --pkce --sans-verifier"
    )
    assert res.rc != 2, message(
        en=f"The flow tool could not measure: {res.stderr.strip()[:300]}",
        fr=f"L'outil de flux n'a pas pu mesurer : {res.stderr.strip()[:300]}",
    )
    refuse = json.loads(res.stdout)
    assert refuse.get("echange_http") == 400, message(
        en="Keycloak accepted a code exchange WITHOUT a PKCE verifier "
        f"(HTTP {refuse.get('echange_http')}). The attribute is therefore set "
        f"without effect. Answer: {str(refuse.get('jetons'))[:300]}",
        fr="Keycloak a accepté un échange de code SANS vérifieur PKCE "
        f"(HTTP {refuse.get('echange_http')}). L'attribut est donc posé sans "
        f"effet. Réponse : {str(refuse.get('jetons'))[:300]}",
    )


def test_aucun_octroi_dangereux_n_a_ete_ouvert(idp):
    """Le quatrième contournement : ouvrir un autre chemin.

    Vert avant le travail ? Non : le client n'existe pas encore dans son état
    final, et une des pannes ferme justement le flux standard.

    Quand le flux de code refuse, il est tentant d'ouvrir l'octroi par mot de
    passe « juste pour vérifier », puis de l'oublier. Il fait passer le mot de
    passe de l'utilisateur par l'application, ce que tout le flux de code
    existe pour éviter.
    """
    client = _client_declare(idp)

    assert client.get("standardFlowEnabled") is True, message(
        en="The authorization code flow is closed. That may have been the breakage: "
        "the fix is to open it again, and it is the only one this client must "
        "use.",
        fr="Le flux de code d'autorisation est fermé. C'était peut-être la panne : "
        "la correction est de le réouvrir, et c'est le seul que ce client doit "
        "employer.",
    )
    assert client.get("implicitFlowEnabled") is False, message(
        en="The implicit flow was opened. It returns the token in the URL, hence in "
        "the browser's history and in the logs of intermediate "
        "servers. RFC 9700 forbids it.",
        fr="Le flux implicite a été ouvert. Il rend le jeton dans l'URL, donc dans "
        "l'historique du navigateur et dans les journaux des serveurs "
        "intermédiaires. La RFC 9700 le proscrit.",
    )
    assert client.get("directAccessGrantsEnabled") is False, message(
        en="The password grant was opened. It makes the application see the "
        "password, and it repairs none of this lab's breakages: it works "
        "around one.",
        fr="L'octroi par mot de passe a été ouvert. Il fait voir le mot de passe "
        "à l'application, et il ne répare aucune des pannes de ce lab : il en "
        "contourne une.",
    )
    assert client.get("serviceAccountsEnabled") is False, message(
        en="The service account was opened on a public client, which makes no "
        "sense: with no secret, anyone could use it.",
        fr="Le compte de service a été ouvert sur un client public, ce qui n'a pas "
        "de sens : sans secret, n'importe qui pourrait s'en servir.",
    )


def test_l_application_s_adresse_toujours_au_bon_realm(idp):
    """Le cinquième contournement : déplacer le problème ailleurs.

    Vert avant le travail ? Non : une des pannes modifie justement cet
    `issuer`, et le test est alors rouge.

    Un `issuer` qui pointe le realm des administrateurs du serveur donne une
    connexion qui RÉUSSIT, avec les mauvaises personnes. C'est la panne la plus
    sournoise des cinq, parce que la corriger au hasard en déplaçant d'autres
    réglages peut produire un flux qui marche et qui n'authentifie pas les
    bonnes gens.
    """
    etat = _etat_temoin(idp)

    assert etat.get("configuration_lue") is True, message(
        en="The application runs but does not read its configuration: "
        f"{etat.get('configuration_erreur')}.",
        fr="L'application tourne mais ne lit pas sa configuration : "
        f"{etat.get('configuration_erreur')}.",
    )
    attendu = f"{KEYCLOAK}/realms/{REALM}"
    assert etat.get("issuer") == attendu, message(
        en=f"The application talks to {etat.get('issuer')!r} instead of "
        f"{attendu!r}. A realm serves one population: the one of the "
        "server's administrators is not the one of an application's "
        "users.",
        fr=f"L'application s'adresse à {etat.get('issuer')!r} au lieu de "
        f"{attendu!r}. Un realm sert une population : celui des "
        "administrateurs du serveur n'est pas celui des utilisateurs d'une "
        "application.",
    )
    assert etat.get("client_id") == CLIENT, message(
        en=f"The application presents itself as {etat.get('client_id')!r} instead of "
        f"{CLIENT!r}.",
        fr=f"L'application se présente sous {etat.get('client_id')!r} au lieu de "
        f"{CLIENT!r}.",
    )
