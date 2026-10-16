"""Épreuve de niveau 1 : les états vérifiés des labs 02, 03, 04 et 05, réunis.

CE QUE CETTE ÉPREUVE MESURE, ET CE QU'ELLE NE MESURE PAS

Elle ne vérifie pas que des gestes ont été faits : elle lit l'état du système.
Un fournisseur installé à la main, par un script ou par la console passe
pareil, et c'est voulu : l'épreuve note un résultat.

Il n'y a PAS de `hints.yaml` : c'est une mesure.

LES FAITS MESURÉS QUI DÉCIDENT DE CES TESTS, tous relevés le 2026-10-16 en
jouant les labs dont cette épreuve est tirée :

1. `start-dev` ignore la base qu'on lui déclare et perd tout au redémarrage.
   La durabilité se vérifie donc en REDÉMARRANT le fournisseur et en relisant
   ce qu'il connaît, pas en lisant sa configuration.

2. Depuis le conteneur du fournisseur, `127.0.0.1:3890` est FERMÉ : c'est le
   conteneur lui-même. L'annuaire de cette épreuve publie son port sur la
   machine, et c'est l'adresse de la machine qu'il faut viser.

3. Déclarer une fédération n'importe personne : il faut demander la
   synchronisation. Une configuration juste et non synchronisée laisse un realm
   qui ne connaît personne, sans aucune erreur.

4. `directAccessGrantsEnabled` est ACTIF par défaut sur un client créé par
   l'API : il doit être fermé explicitement sur une application publique.

5. Déclarer un scope ne met rien dans `aud`. L'audience arrive par un mappeur,
   et sans elle une API qui vérifie `aud` refuse tout, tandis qu'une API qui ne
   la vérifie pas accepte les jetons destinés à n'importe qui.
"""

from __future__ import annotations

import json
import shlex

import pytest

from conftest import lab_host, lab_target_host, message

# L'hôte RÉELLEMENT testé. `dsoxlab check --target` peut en imposer un autre,
# et coder le nom en dur ferait tester la cible par défaut en prétendant tester
# celle qu'on a demandée.
CIBLE = lab_target_host("idp.lab")

IDENTIFIANTS = "/opt/iam-lab/identifiants-lab.txt"


@pytest.fixture(scope="module")
def idp():
    """La machine de l'épreuve.

    `lab_host` est une fonction du conftest, pas une fixture : chaque lab bâtit
    la sienne, ce qui permet à un lab multi-hôtes d'en avoir plusieurs.
    """
    return lab_host(CIBLE)


# ── Outils de lecture de l'état ──────────────────────────────────────────────


def _cahier(hote) -> dict[str, str]:
    """Le cahier des charges que le setup a écrit.

    Aucune valeur attendue n'est codée dans ces tests : elles viennent toutes
    de ce fichier, qui est aussi ce que la candidate a lu.
    """
    fichier = hote.file(IDENTIFIANTS)
    assert fichier.exists, message(
        en=f"{IDENTIFIANTS} is missing. The exam's setup did not run, or "
        "its staging script failed: the trace is in "
        "/var/log/dsoxlab-prepare.log on the machine.",
        fr=f"{IDENTIFIANTS} est absent. Le setup de l'épreuve n'a pas tourné, ou "
        "son script de mise en situation a échoué : la trace est dans "
        "/var/log/dsoxlab-prepare.log sur la machine.",
    )
    valeurs = {}
    for ligne in fichier.content_string.splitlines():
        if "=" in ligne and not ligne.startswith("#"):
            clef, _, valeur = ligne.partition("=")
            valeurs[clef.strip()] = valeur.strip()
    return valeurs


def _jeton_admin(hote, cahier: dict[str, str]) -> str:
    """Un jeton d'administration, par le compte NOMINATIF attendu.

    C'est aussi un contrôle : si ce compte n'existe pas, l'épreuve ne peut pas
    être notée, et le message le dit plutôt que de laisser dix tests échouer
    sur des causes inventées.
    """
    res = hote.run(
        f"curl -sS --max-time 20 -X POST "
        f"{cahier['URL_KEYCLOAK_ATTENDUE']}/realms/master/protocol/"
        "openid-connect/token "
        f"-d grant_type=password -d client_id=admin-cli "
        f"-d username={shlex.quote(cahier['ADMIN_NOMINATIF_ATTENDU'])} "
        f"-d password={shlex.quote(cahier['ADMIN_MOT_DE_PASSE'])}")
    try:
        charge = json.loads(res.stdout)
    except json.JSONDecodeError:
        pytest.fail(
            message(
            en="The provider did not answer in JSON on its token endpoint. "
            f"Is it in service on {cahier['URL_KEYCLOAK_ATTENDUE']}? "
            f"Answer: {res.stdout[:200]!r}",
            fr="Le fournisseur n'a pas répondu en JSON sur son point de jeton. "
            f"Est-il en service sur {cahier['URL_KEYCLOAK_ATTENDUE']} ? "
            f"Réponse : {res.stdout[:200]!r}",
        ))
    jeton = charge.get("access_token", "")
    assert jeton, message(
        en=f"The account \"{cahier['ADMIN_NOMINATIF_ATTENDU']}\" does not obtain "
        f"an administration token: {json.dumps(charge)[:250]}. The "
        "specification asks for that account, with the password it gives.",
        fr=f"Le compte « {cahier['ADMIN_NOMINATIF_ATTENDU']} » n'obtient pas de "
        f"jeton d'administration : {json.dumps(charge)[:250]}. Le cahier des "
        "charges demande ce compte, avec le mot de passe qu'il donne.",
    )
    return jeton


def _api(hote, cahier: dict[str, str], jeton: str, chemin: str, *,
         brut: bool = False):
    # L'URL EST QUOTÉE, et ce n'est pas une précaution de style : un chemin
    # comme `users?username=x&exact=true` contient un `&`, qui coupe la
    # commande du shell. `curl` part alors sans son en-tête d'autorisation, le
    # fournisseur répond 401, et le test accuse la fédération de ne pas avoir
    # importé le compte. Vécu le 2026-10-16.
    res = hote.run(
        f"curl -sS --max-time 30 "
        f"{shlex.quote(cahier['URL_KEYCLOAK_ATTENDUE'] + '/admin/' + chemin)} "
        f"-H {shlex.quote('Authorization: Bearer ' + jeton)}")
    if brut:
        return res.stdout
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        pytest.fail(message(
            en=f"/admin/{chemin} returned no JSON: "
                    f"{res.stdout[:200]!r}",
            fr=f"/admin/{chemin} n'a pas rendu de JSON : "
                    f"{res.stdout[:200]!r}",
        ))


def _client(hote, cahier: dict[str, str], jeton: str, nom: str) -> dict:
    trouves = _api(hote, cahier, jeton,
                   f"realms/{cahier['REALM_ATTENDU']}/clients?clientId={nom}")
    assert isinstance(trouves, list) and trouves, message(
        en=f"The client \"{nom}\" does not exist in the realm "
        f"\"{cahier['REALM_ATTENDU']}\". The specification names it.",
        fr=f"Le client « {nom} » n'existe pas dans le realm "
        f"« {cahier['REALM_ATTENDU']} ». Le cahier des charges le nomme.",
    )
    return trouves[0]


def _jeton_utilisateur(hote, cahier: dict[str, str], *, scope: str = "") -> dict:
    """Un jeton de la personne de test, par le client d'octroi direct.

    Rendu tel quel, avec son code HTTP : plusieurs tests ont besoin de savoir
    non seulement si le jeton arrive, mais ce que le fournisseur répond quand
    il n'arrive pas.
    """
    demande = (
        f"-d grant_type=password "
        f"-d client_id={shlex.quote(cahier['CLIENT_DE_TEST_ATTENDU'])} "
        f"-d username={shlex.quote(cahier['UTILISATEUR'])} "
        f"-d password={shlex.quote(cahier['MOT_DE_PASSE'])}")
    if scope:
        demande += f" -d scope={shlex.quote('openid ' + scope)}"
    res = hote.run(
        f"curl -sS --max-time 20 "
        f"{cahier['URL_KEYCLOAK_ATTENDUE']}/realms/{cahier['REALM_ATTENDU']}"
        f"/protocol/openid-connect/token {demande}")
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        pytest.fail(message(
            en=f"The token endpoint returned no JSON: "
                    f"{res.stdout[:200]!r}",
            fr=f"Le point de jeton n'a pas rendu de JSON : "
                    f"{res.stdout[:200]!r}",
        ))


# ── Lab 02 : un fournisseur qui dure ────────────────────────────────────────


def test_le_fournisseur_est_en_service_avec_un_compte_nominatif(idp):
    """Il répond, son port de gestion répond, et le compte de démarrage a été
    retiré.

    Le compte de démarrage est un compte partagé, sans nom de personne : le
    garder revient à n'avoir aucune traçabilité des gestes d'administration.
    """
    cahier = _cahier(idp)
    jeton = _jeton_admin(idp, cahier)

    sante = idp.run(
        f"curl -sS --max-time 10 "
        f"http://127.0.0.1:{cahier['PORT_GESTION_ATTENDU']}/health/ready")
    assert '"UP"' in sante.stdout, message(
        en="The management port does not declare the provider ready: "
        f"{sante.stdout[:200]!r}. Health and metrics live on port "
        f"{cahier['PORT_GESTION_ATTENDU']}, and not on the application's.",
        fr="Le port de gestion ne déclare pas le fournisseur prêt : "
        f"{sante.stdout[:200]!r}. La santé et les métriques vivent sur le port "
        f"{cahier['PORT_GESTION_ATTENDU']}, et non sur celui de "
        "l'application.",
    )

    comptes = _api(idp, cahier, jeton, "realms/master/users?max=100")
    noms = {c.get("username") for c in comptes}
    assert cahier["ADMIN_NOMINATIF_ATTENDU"] in noms, message(
        en=f"The named account \"{cahier['ADMIN_NOMINATIF_ATTENDU']}\" is not "
        f"in the master realm: {sorted(noms)}",
        fr=f"Le compte nominatif « {cahier['ADMIN_NOMINATIF_ATTENDU']} » n'est "
        f"pas dans le realm master : {sorted(noms)}",
    )
    restants = noms & {"temp-admin", "admin", "bootstrap", "kcadmin"}
    assert not restants, message(
        en=f"A bootstrap account remained in the master realm: {restants}. "
        "A shared account administering the server leaves no trace of who "
        "did what.",
        fr=f"Un compte de démarrage est resté dans le realm master : {restants}. "
        "Un compte partagé qui administre le serveur ne laisse aucune trace de "
        "qui a fait quoi.",
    )


def test_le_fournisseur_survit_a_un_redemarrage(idp):
    """LA durabilité ne se lit pas dans une configuration, elle se mesure.

    `start-dev` ignore la base qu'on lui déclare, embarque une base en fichier,
    et perd tout au redémarrage. Ce test crée une marque, redémarre le
    conteneur, et vérifie que la marque est toujours là.
    """
    cahier = _cahier(idp)
    jeton = _jeton_admin(idp, cahier)
    realm = cahier["REALM_ATTENDU"]
    marque = "marque-de-durabilite"

    pose = idp.run(
        f"curl -sS --max-time 20 -o /dev/null -w '%{{http_code}}' -X POST "
        f"{cahier['URL_KEYCLOAK_ATTENDUE']}/admin/realms/{realm}/groups "
        f"-H {shlex.quote('Authorization: Bearer ' + jeton)} "
        "-H 'Content-Type: application/json' "
        f"-d {shlex.quote(json.dumps({'name': marque}))}")
    assert pose.stdout.strip() in ("201", "409"), message(
        en=f"No mark could be placed in the realm: HTTP "
        f"{pose.stdout.strip()}",
        fr=f"Impossible de poser une marque dans le realm : HTTP "
        f"{pose.stdout.strip()}",
    )

    conteneur = idp.run(
        "docker ps --filter 'name=keycloak' --format '{{.Names}}' | head -n 1")
    nom = conteneur.stdout.strip()
    assert nom, message(
        en="No container whose name contains \"keycloak\": is the provider "
        "running in a container?",
        fr="Aucun conteneur dont le nom contient « keycloak » : le fournisseur "
        "tourne-t-il dans un conteneur ?",
    )

    redemarrage = idp.run(f"docker restart {shlex.quote(nom)}")
    assert redemarrage.rc == 0, message(
        en=f"The container {nom} did not restart: {redemarrage.stderr[:200]!r}",
        fr=f"Le conteneur {nom} n'a pas redémarré : {redemarrage.stderr[:200]!r}",
    )

    attente = idp.run(
        "for i in $(seq 1 60); do "
        "code=$(curl -sS --max-time 3 -o /dev/null -w '%{http_code}' "
        f"http://127.0.0.1:{cahier['PORT_GESTION_ATTENDU']}/health/ready "
        "2>/dev/null || true); "
        '[ "$code" = "200" ] && { echo pret; break; }; sleep 2; done')
    assert "pret" in attente.stdout, message(
        en="The provider did not come back within two minutes of its "
        "restart.",
        fr="Le fournisseur n'est pas revenu dans les deux minutes après son "
        "redémarrage.",
    )

    jeton = _jeton_admin(idp, cahier)
    groupes = _api(idp, cahier, jeton, f"realms/{realm}/groups?max=200")
    noms = {g.get("name") for g in groupes}
    assert marque in noms, message(
        en="The mark placed before the restart has disappeared: the data does "
        "not survive. That is the symptom of `start-dev`, which ignores the "
        "declared database and ships its own, in a file, inside the container.",
        fr="La marque posée avant le redémarrage a disparu : les données ne "
        "survivent pas. C'est le symptôme de `start-dev`, qui ignore la base "
        "déclarée et embarque la sienne, en fichier, dans le conteneur.",
    )

    # La marque est retirée : un test ne laisse pas de trace de son passage.
    cible = next(g for g in groupes if g.get("name") == marque)
    idp.run(
        f"curl -sS --max-time 20 -X DELETE "
        f"{cahier['URL_KEYCLOAK_ATTENDUE']}/admin/realms/{realm}/groups/"
        f"{cible['id']} "
        f"-H {shlex.quote('Authorization: Bearer ' + jeton)}")


# ── Lab 03 : l'annuaire fédéré ──────────────────────────────────────────────


def test_les_comptes_de_l_annuaire_sont_connus_du_realm(idp):
    """Les trois comptes de l'annuaire sont dans le realm, et s'y connectent.

    Déclarer la fédération n'importe personne : la synchronisation se demande.
    Une configuration juste et non synchronisée laisse un realm vide sans
    aucune erreur.
    """
    cahier = _cahier(idp)
    jeton = _jeton_admin(idp, cahier)
    attendus = set(cahier["LDAP_COMPTES"].split())

    comptes = _api(idp, cahier, jeton,
                   f"realms/{cahier['REALM_ATTENDU']}/users?max=200")
    presents = {c.get("username") for c in comptes}
    manquants = attendus - presents
    assert not manquants, message(
        en=f"Directory accounts missing from the realm: {sorted(manquants)}. "
        f"Present: {sorted(presents)}. Is the federation declared, and "
        "was the synchronisation REQUESTED?",
        fr=f"Comptes de l'annuaire absents du realm : {sorted(manquants)}. "
        f"Présents : {sorted(presents)}. La fédération est-elle déclarée, et "
        "la synchronisation a-t-elle été DEMANDÉE ?",
    )

    jetons = _jeton_utilisateur(idp, cahier)
    assert "access_token" in jetons, message(
        en=f"\"{cahier['UTILISATEUR']}\" does not log in through the "
        f"provider: {json.dumps(jetons)[:250]}. The accounts are present "
        "but the authentication does not reach the directory: is the "
        "federation's connection address reachable FROM THE CONTAINER?",
        fr=f"« {cahier['UTILISATEUR']} » ne se connecte pas à travers le "
        f"fournisseur : {json.dumps(jetons)[:250]}. Les comptes sont présents "
        "mais l'authentification ne remonte pas à l'annuaire : l'adresse de "
        "connexion de la fédération est-elle joignable DEPUIS LE CONTENEUR ?",
    )


def test_les_groupes_de_l_annuaire_portent_leurs_membres(idp):
    """Les groupes ne suivent pas les comptes tout seuls.

    Il faut un second composant, et une seconde synchronisation. Un mappeur qui
    lit le mauvais attribut d'appartenance importe des groupes VIDES, ce qui
    est le défaut le plus discret du lab dont ce test est tiré.
    """
    cahier = _cahier(idp)
    jeton = _jeton_admin(idp, cahier)
    realm = cahier["REALM_ATTENDU"]
    devops = cahier["LDAP_GROUPE_DEVOPS"]

    groupes = _api(idp, cahier, jeton, f"realms/{realm}/groups?max=200")
    par_nom = {g.get("name"): g for g in groupes}
    assert devops in par_nom, message(
        en=f"The directory's group \"{devops}\" is not in the realm: "
        f"{sorted(par_nom)}. Is the group mapper declared, and was the "
        "mapper's synchronisation requested?",
        fr=f"Le groupe « {devops} » de l'annuaire n'est pas dans le realm : "
        f"{sorted(par_nom)}. Le mappeur de groupes est-il déclaré, et la "
        "synchronisation du mappeur demandée ?",
    )

    membres = _api(idp, cahier, jeton,
                   f"realms/{realm}/groups/{par_nom[devops]['id']}"
                   "/members?max=200")
    noms = sorted(m.get("username") for m in membres)
    assert noms == ["aline", "bruno"], message(
        en=f"The group \"{devops}\" carries {noms} instead of ['aline', 'bruno']. "
        "A group imported but empty is the sign that the mapper reads "
        "membership in the wrong attribute.",
        fr=f"Le groupe « {devops} » porte {noms} au lieu de ['aline', 'bruno']. "
        "Un groupe importé mais vide est le signe que le mappeur lit "
        "l'appartenance dans le mauvais attribut.",
    )


# ── Lab 04 : l'application branchée ─────────────────────────────────────────


def test_l_application_est_declaree_en_client_public_avec_pkce(idp):
    """Public, flux de code, PKCE S256, et les flux dangereux fermés.

    `directAccessGrantsEnabled` est ACTIF par défaut sur un client créé par
    l'API : il doit être fermé explicitement, sinon l'application peut
    récupérer le mot de passe de l'usager.
    """
    cahier = _cahier(idp)
    jeton = _jeton_admin(idp, cahier)
    client = _client(idp, cahier, jeton, cahier["CLIENT_APPLI_ATTENDU"])

    assert client.get("publicClient") is True, message(
        en=f"\"{cahier['CLIENT_APPLI_ATTENDU']}\" is not public. An "
        "application running at the user's keeps no secret.",
        fr=f"« {cahier['CLIENT_APPLI_ATTENDU']} » n'est pas public. Une "
        "application qui tourne chez l'usager ne garde aucun secret.",
    )
    assert client.get("standardFlowEnabled") is True, message(
        en="The authorization code flow is closed: the application cannot have "
        "anyone authenticated.",
        fr="Le flux de code d'autorisation est fermé : l'application ne peut pas "
        "faire authentifier qui que ce soit.",
    )
    assert client.get("implicitFlowEnabled") is False, message(
        en="The implicit flow is open. It returns the token in the URL, where it "
        "ends up in the history and in the server's logs, and RFC 9700 "
        "forbids it.",
        fr="Le flux implicite est ouvert. Il rend le jeton dans l'URL, où il "
        "finit dans l'historique et les journaux du serveur, et la RFC 9700 le "
        "proscrit.",
    )
    assert client.get("directAccessGrantsEnabled") is False, message(
        en="The direct password grant is open on the application. It is "
        "ACTIVE BY DEFAULT: closing it is an explicit gesture, and leaving it "
        "makes the user's password pass through the application.",
        fr="L'octroi direct par mot de passe est ouvert sur l'application. Il est "
        "ACTIF PAR DÉFAUT : le fermer est un geste explicite, et le laisser "
        "fait passer le mot de passe de l'usager par l'application.",
    )
    assert client.get("attributes", {}).get(
        "pkce.code.challenge.method") == "S256", message(
        en="PKCE S256 is not required. Without it, an authorization code "
        "intercepted on the workstation is enough to obtain a token.",
        fr="PKCE S256 n'est pas exigé. Sans lui, un code d'autorisation "
        "intercepté sur le poste suffit à obtenir un jeton.",
    )
    jokers = [u for u in client.get("redirectUris") or [] if u.endswith("/*")
              or u == "*"]
    assert not jokers, message(
        en=f"Some redirect URIs carry a wildcard: {jokers}. A redirection "
        "that is too broad allows the authorization code to be sent elsewhere.",
        fr=f"Des URI de redirection portent un joker : {jokers}. Une redirection "
        "trop large laisse envoyer le code d'autorisation ailleurs.",
    )


def test_le_parcours_de_connexion_aboutit(idp):
    """Le témoin part de l'application, passe par le fournisseur, et revient.

    C'est le seul contrôle qui juge l'intégration plutôt que sa déclaration :
    un client parfaitement déclaré et une application mal configurée donnent
    une page de connexion qui renvoie sur elle-même.
    """
    cahier = _cahier(idp)
    depart = f"http://127.0.0.1:{cahier['PORT_APPLI_TEMOIN']}/connexion"

    etat = idp.run(
        f"curl -sS --max-time 10 "
        f"http://127.0.0.1:{cahier['PORT_APPLI_TEMOIN']}/etat")
    assert etat.rc == 0 and etat.stdout.strip(), message(
        en="The witness application does not answer on its port "
        f"{cahier['PORT_APPLI_TEMOIN']}: it was not started.",
        fr="L'application témoin ne répond pas sur son port "
        f"{cahier['PORT_APPLI_TEMOIN']} : elle n'a pas été démarrée.",
    )
    try:
        config = json.loads(etat.stdout)
    except json.JSONDecodeError:
        pytest.fail(message(
            en=f"The witness's state is not JSON: "
                    f"{etat.stdout[:200]!r}",
            fr=f"L'état du témoin n'est pas du JSON : "
                    f"{etat.stdout[:200]!r}",
        ))
    assert config.get("configuration_lue"), message(
        en=f"The witness application reads no configuration: "
        f"{json.dumps(config)[:200]}",
        fr=f"L'application témoin ne lit aucune configuration : "
        f"{json.dumps(config)[:200]}",
    )
    attendu = (f"{cahier['URL_KEYCLOAK_ATTENDUE']}/realms/"
               f"{cahier['REALM_ATTENDU']}")
    assert config.get("issuer") == attendu, message(
        en=f"The application points at the issuer \"{config.get('issuer')}\" and not "
        f"\"{attendu}\". A notes application does not authenticate the "
        "server's administrators.",
        fr=f"L'application pointe sur l'issuer « {config.get('issuer')} » et non "
        f"« {attendu} ». Une application de notes n'authentifie pas les "
        "administrateurs du serveur.",
    )

    res = idp.run(
        "timeout 90 python3 -I /opt/iam-lab/outils/parcours.py "
        f"--depart {shlex.quote(depart)} "
        f"--utilisateur {shlex.quote(cahier['UTILISATEUR'])} "
        f"--mot-de-passe {shlex.quote(cahier['MOT_DE_PASSE'])}")
    assert res.rc != 2, message(
        en="The journey witness could not measure, which is not the same thing "
        f"as a broken integration:\n{res.stdout}{res.stderr}",
        fr="Le témoin de parcours n'a pas pu mesurer, ce qui n'est pas la même "
        f"chose qu'une intégration cassée :\n{res.stdout}{res.stderr}",
    )
    try:
        parcours = json.loads(res.stdout)
    except json.JSONDecodeError:
        pytest.fail(message(
            en=f"The witness returned no JSON at all:\n{res.stdout[:400]}",
            fr=f"Le témoin n'a rendu aucun JSON :\n{res.stdout[:400]}",
        ))

    assert parcours["connexion_posee"], message(
        en="The journey never met the provider's login form: the "
        "application does not delegate the authentication.\n"
        f"steps: {json.dumps(parcours['etapes'])}",
        fr="Le parcours n'a jamais rencontré le formulaire de connexion du "
        "fournisseur : l'application ne délègue pas l'authentification.\n"
        f"étapes : {json.dumps(parcours['etapes'])}",
    )
    assert parcours["http"] == 200, message(
        en=f"The journey ends on HTTP {parcours['http']} at "
        f"{parcours['arrivee']}.",
        fr=f"Le parcours finit sur HTTP {parcours['http']} à "
        f"{parcours['arrivee']}.",
    )
    assert cahier["UTILISATEUR"] in parcours.get("texte", ""), message(
        en="The application does not show the name of the logged-in person at "
        f"the arrival ({parcours['arrivee']}). Is the token validated and read?",
        fr="L'application ne montre pas le nom de la personne connectée à "
        f"l'arrivée ({parcours['arrivee']}). Le jeton est-il validé et lu ?",
    )


# ── Lab 05 : l'API fermée ───────────────────────────────────────────────────


def test_l_api_refuse_sans_jeton_et_accepte_avec_le_bon(idp):
    """401 sans jeton, 200 avec un jeton qui porte l'audience et le scope."""
    cahier = _cahier(idp)
    url = f"http://127.0.0.1:{cahier['PORT_API']}/notes"

    sans = idp.run(
        f"curl -sS --max-time 10 -o /dev/null -w '%{{http_code}}' {url}")
    assert sans.stdout.strip() == "401", message(
        en=f"The API answers HTTP {sans.stdout.strip()} with no token at all, "
        "instead of 401. An API serving data without knowing to whom is the "
        "defect this exam exists to close.",
        fr=f"L'API répond HTTP {sans.stdout.strip()} sans aucun jeton, au lieu "
        "de 401. Une API qui sert des données sans savoir à qui est le défaut "
        "que cette épreuve existe pour fermer.",
    )

    jetons = _jeton_utilisateur(idp, cahier, scope=cahier["SCOPE_LECTURE"])
    assert "access_token" in jetons, message(
        en=f"No token with the scope \"{cahier['SCOPE_LECTURE']}\": "
        f"{json.dumps(jetons)[:250]}. Does the scope exist, and is it attached "
        "to the test client?",
        fr=f"Pas de jeton avec le scope « {cahier['SCOPE_LECTURE']} » : "
        f"{json.dumps(jetons)[:250]}. Le scope existe-t-il, et est-il attaché "
        "au client de test ?",
    )
    avec = idp.run(
        f"curl -sS --max-time 10 -o /dev/null -w '%{{http_code}}' {url} "
        f"-H {shlex.quote('Authorization: Bearer ' + jetons['access_token'])}")
    assert avec.stdout.strip() == "200", message(
        en=f"The API answers HTTP {avec.stdout.strip()} with a token that does "
        "carry the read scope. Does it check the right audience, and is the "
        "audience mapper set on the scope?",
        fr=f"L'API répond HTTP {avec.stdout.strip()} avec un jeton pourtant "
        "porteur du scope de lecture. Vérifie-t-elle la bonne audience, et le "
        "mappeur d'audience est-il posé sur le scope ?",
    )


def test_l_api_distingue_l_authentification_de_l_autorisation(idp):
    """403 sur un jeton valide dont le scope ne suffit pas.

    401 dit « je ne sais pas qui vous êtes », et un client réessaie en
    s'authentifiant. 403 dit « je sais qui vous êtes, et cela ne suffit pas »,
    et réessayer ne servirait à rien. Confondre les deux envoie le client dans
    une boucle.
    """
    cahier = _cahier(idp)
    url = f"http://127.0.0.1:{cahier['PORT_API']}/notes"

    jetons = _jeton_utilisateur(idp, cahier, scope=cahier["SCOPE_LECTURE"])
    assert "access_token" in jetons, message(
        en="No read token.",
        fr="Pas de jeton de lecture.",
    )

    ecriture = idp.run(
        f"curl -sS --max-time 10 -o /dev/null -w '%{{http_code}}' -X POST "
        f"{url} -H {shlex.quote('Authorization: Bearer ' + jetons['access_token'])} "
        "-H 'Content-Type: application/json' -d '{}'")
    assert ecriture.stdout.strip() == "403", message(
        en=f"A write with a READ token answers HTTP "
        f"{ecriture.stdout.strip()} instead of 403. If it is 200, the scope "
        "is not checked; if it is 401, the API confuses \"I do not know you\" "
        "with \"that is not enough\".",
        fr=f"Une écriture avec un jeton de LECTURE répond HTTP "
        f"{ecriture.stdout.strip()} au lieu de 403. Si c'est 200, le scope "
        "n'est pas vérifié ; si c'est 401, l'API confond « je ne vous connais "
        "pas » et « cela ne suffit pas ».",
    )


def test_l_api_refuse_un_jeton_destine_a_une_autre_application(idp):
    """LE contrôle central du lab 05, et la faille la plus répandue.

    Un jeton émis par le même fournisseur, pour le même usager, et destiné à
    une autre application, est parfaitement valide. Une API qui ne vérifie pas
    `aud` l'accepte, et toute application du realm peut alors parler à toutes
    les autres.
    """
    cahier = _cahier(idp)
    url = f"http://127.0.0.1:{cahier['PORT_API']}/notes"

    jetons = _jeton_utilisateur(idp, cahier, scope=cahier["SCOPE_AUTRE_API"])
    assert "access_token" in jetons, message(
        en=f"No token with the scope \"{cahier['SCOPE_AUTRE_API']}\": this "
        "test needs a token intended for ANOTHER application in order to "
        f"measure anything. {json.dumps(jetons)[:200]}",
        fr=f"Pas de jeton avec le scope « {cahier['SCOPE_AUTRE_API']} » : ce "
        "test a besoin d'un jeton destiné à une AUTRE application pour "
        f"mesurer quoi que ce soit. {json.dumps(jetons)[:200]}",
    )
    res = idp.run(
        f"curl -sS --max-time 10 -o /dev/null -w '%{{http_code}}' {url} "
        f"-H {shlex.quote('Authorization: Bearer ' + jetons['access_token'])}")
    assert res.stdout.strip() == "401", message(
        en=f"The API accepts (HTTP {res.stdout.strip()}) a token intended for "
        "another application. It does not check `aud`, and any "
        "application of the realm can talk to it.",
        fr=f"L'API accepte (HTTP {res.stdout.strip()}) un jeton destiné à une "
        "autre application. Elle ne vérifie pas `aud`, et n'importe quelle "
        "application du realm peut lui parler.",
    )


def test_un_service_machine_accede_en_lecture_et_pas_en_ecriture(idp):
    """Un accès machine, borné, et borné du bon côté.

    En client credentials, personne ne demande de scope : seuls les scopes PAR
    DÉFAUT arrivent dans le jeton. Et un service de sauvegarde lit : lui donner
    l'écriture parce que c'est plus simple est la façon ordinaire de perdre des
    données, sans que personne surveille.
    """
    cahier = _cahier(idp)
    jeton = _jeton_admin(idp, cahier)
    service = _client(idp, cahier, jeton, cahier["CLIENT_SERVICE_ATTENDU"])

    assert service.get("serviceAccountsEnabled") is True, message(
        en=f"\"{cahier['CLIENT_SERVICE_ATTENDU']}\" has no service "
        "account: it cannot authenticate with nobody.",
        fr=f"« {cahier['CLIENT_SERVICE_ATTENDU']} » n'a pas de compte de "
        "service : il ne peut pas s'authentifier sans personne.",
    )
    assert service.get("publicClient") is False, message(
        en="A service authenticating on its own must be confidential: with no "
        "secret, anyone can present themselves in its name.",
        fr="Un service qui s'authentifie seul doit être confidentiel : sans "
        "secret, n'importe qui peut se présenter en son nom.",
    )

    secret = _api(idp, cahier, jeton,
                  f"realms/{cahier['REALM_ATTENDU']}/clients/"
                  f"{service['id']}/client-secret")
    assert isinstance(secret, dict) and secret.get("value"), message(
        en=f"The service has no secret: {json.dumps(secret)[:200]}",
        fr=f"Le service n'a pas de secret : {json.dumps(secret)[:200]}",
    )

    jetons = idp.run(
        f"curl -sS --max-time 20 "
        f"{cahier['URL_KEYCLOAK_ATTENDUE']}/realms/{cahier['REALM_ATTENDU']}"
        "/protocol/openid-connect/token "
        "-d grant_type=client_credentials "
        f"-d client_id={shlex.quote(cahier['CLIENT_SERVICE_ATTENDU'])} "
        f"-d client_secret={shlex.quote(secret['value'])}")
    try:
        charge = json.loads(jetons.stdout)
    except json.JSONDecodeError:
        pytest.fail(message(
            en=f"No JSON at the token endpoint: {jetons.stdout[:200]!r}",
            fr=f"Pas de JSON au point de jeton : {jetons.stdout[:200]!r}",
        ))
    assert "access_token" in charge, message(
        en=f"The service does not obtain a token: {json.dumps(charge)[:250]}",
        fr=f"Le service n'obtient pas de jeton : {json.dumps(charge)[:250]}",
    )

    url = f"http://127.0.0.1:{cahier['PORT_API']}/notes"
    entete = shlex.quote("Authorization: Bearer " + charge["access_token"])
    lecture = idp.run(
        f"curl -sS --max-time 10 -o /dev/null -w '%{{http_code}}' {url} "
        f"-H {entete}")
    assert lecture.stdout.strip() == "200", message(
        en=f"The service does not read the API (HTTP {lecture.stdout.strip()}). In "
        "client credentials, only the DEFAULT scopes arrive in the "
        "token: is the read scope attached by default to that client?",
        fr=f"Le service ne lit pas l'API (HTTP {lecture.stdout.strip()}). En "
        "client credentials, seuls les scopes PAR DÉFAUT arrivent dans le "
        "jeton : le scope de lecture est-il attaché par défaut à ce client ?",
    )
    ecriture = idp.run(
        f"curl -sS --max-time 10 -o /dev/null -w '%{{http_code}}' -X POST "
        f"{url} -H {entete} -H 'Content-Type: application/json' -d '{{}}'")
    assert ecriture.stdout.strip() == "403", message(
        en=f"The service WRITES into the API (HTTP {ecriture.stdout.strip()}). A "
        "backup service reads. A machine access that is too broad is more "
        "dangerous than a human one, because nobody watches it.",
        fr=f"Le service ÉCRIT dans l'API (HTTP {ecriture.stdout.strip()}). Un "
        "service de sauvegarde lit. Un accès machine trop large est plus "
        "dangereux qu'un accès humain, parce que personne ne le surveille.",
    )
