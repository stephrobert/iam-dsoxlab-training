"""Épreuve finale : les états vérifiés des labs 02 à 09, réunis.

CE QUE CETTE ÉPREUVE MESURE, ET CE QU'ELLE NE MESURE PAS

Elle ne vérifie pas que des gestes ont été faits : elle lit l'état du système.
Un fournisseur installé à la main, par un script ou par la console passe
pareil, et c'est voulu : l'épreuve note un résultat.

Il n'y a PAS de `hints.yaml` : c'est une mesure.

UNE CONTRAINTE DÉCIDE DU CHOIX DES COMPTES. L'épreuve impose un second
facteur au groupe sensible, et le compte qui joue le parcours OIDC n'en est
donc pas membre : sinon son parcours serait arrêté par l'exigence que l'épreuve
demande elle-même de poser, et le test accuserait le branchement OIDC. Le
cahier des charges nomme les trois rôles (`UTILISATEUR`, `COMPTE_CONCERNE`,
`QUI_PART`), et ces tests les lisent là.

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

6. `conditional-user-configured` dans le sous-flux du second facteur n'exige le
   facteur que de ceux qui en ont DÉJÀ un : avec lui, un compte sans second
   facteur se connecte directement, même avec l'étape OTP en REQUIRED. On croit
   avoir imposé le facteur à une équipe, et personne ne l'a.

7. Désactiver un compte NE FERME PAS ses sessions, et retirer une appartenance
   fédérée est refusé par le fournisseur quand le mappeur est en lecture seule :
   elle se retire à la SOURCE, puis se resynchronise, puis le cache des comptes
   fédérés doit être vidé.

8. Un export de realm ne porte AUCUN événement : la trace de qui s'est connecté
   vit dans la base. Une sauvegarde de realm n'est donc pas une sauvegarde.
"""

from __future__ import annotations

import json
import shlex

import pytest

from conftest import lab_host, lab_target_host

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
    assert fichier.exists, (
        f"{IDENTIFIANTS} est absent. Le setup de l'épreuve n'a pas tourné, ou "
        "son script de mise en situation a échoué : la trace est dans "
        "/var/log/dsoxlab-prepare.log sur la machine."
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
            "Le fournisseur n'a pas répondu en JSON sur son point de jeton. "
            f"Est-il en service sur {cahier['URL_KEYCLOAK_ATTENDUE']} ? "
            f"Réponse : {res.stdout[:200]!r}")
    jeton = charge.get("access_token", "")
    assert jeton, (
        f"Le compte « {cahier['ADMIN_NOMINATIF_ATTENDU']} » n'obtient pas de "
        f"jeton d'administration : {json.dumps(charge)[:250]}. Le cahier des "
        "charges demande ce compte, avec le mot de passe qu'il donne."
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
        pytest.fail(f"/admin/{chemin} n'a pas rendu de JSON : "
                    f"{res.stdout[:200]!r}")


def _client(hote, cahier: dict[str, str], jeton: str, nom: str) -> dict:
    trouves = _api(hote, cahier, jeton,
                   f"realms/{cahier['REALM_ATTENDU']}/clients?clientId={nom}")
    assert isinstance(trouves, list) and trouves, (
        f"Le client « {nom} » n'existe pas dans le realm "
        f"« {cahier['REALM_ATTENDU']} ». Le cahier des charges le nomme."
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
        pytest.fail(f"Le point de jeton n'a pas rendu de JSON : "
                    f"{res.stdout[:200]!r}")


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
    assert '"UP"' in sante.stdout, (
        "Le port de gestion ne déclare pas le fournisseur prêt : "
        f"{sante.stdout[:200]!r}. La santé et les métriques vivent sur le port "
        f"{cahier['PORT_GESTION_ATTENDU']}, et non sur celui de "
        "l'application."
    )

    comptes = _api(idp, cahier, jeton, "realms/master/users?max=100")
    noms = {c.get("username") for c in comptes}
    assert cahier["ADMIN_NOMINATIF_ATTENDU"] in noms, (
        f"Le compte nominatif « {cahier['ADMIN_NOMINATIF_ATTENDU']} » n'est "
        f"pas dans le realm master : {sorted(noms)}"
    )
    restants = noms & {"temp-admin", "admin", "bootstrap", "kcadmin"}
    assert not restants, (
        f"Un compte de démarrage est resté dans le realm master : {restants}. "
        "Un compte partagé qui administre le serveur ne laisse aucune trace de "
        "qui a fait quoi."
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
    assert pose.stdout.strip() in ("201", "409"), (
        f"Impossible de poser une marque dans le realm : HTTP "
        f"{pose.stdout.strip()}"
    )

    conteneur = idp.run(
        "docker ps --filter 'name=keycloak' --format '{{.Names}}' | head -n 1")
    nom = conteneur.stdout.strip()
    assert nom, (
        "Aucun conteneur dont le nom contient « keycloak » : le fournisseur "
        "tourne-t-il dans un conteneur ?"
    )

    redemarrage = idp.run(f"docker restart {shlex.quote(nom)}")
    assert redemarrage.rc == 0, (
        f"Le conteneur {nom} n'a pas redémarré : {redemarrage.stderr[:200]!r}"
    )

    attente = idp.run(
        "for i in $(seq 1 60); do "
        "code=$(curl -sS --max-time 3 -o /dev/null -w '%{http_code}' "
        f"http://127.0.0.1:{cahier['PORT_GESTION_ATTENDU']}/health/ready "
        "2>/dev/null || true); "
        '[ "$code" = "200" ] && { echo pret; break; }; sleep 2; done')
    assert "pret" in attente.stdout, (
        "Le fournisseur n'est pas revenu dans les deux minutes après son "
        "redémarrage."
    )

    jeton = _jeton_admin(idp, cahier)
    groupes = _api(idp, cahier, jeton, f"realms/{realm}/groups?max=200")
    noms = {g.get("name") for g in groupes}
    assert marque in noms, (
        "La marque posée avant le redémarrage a disparu : les données ne "
        "survivent pas. C'est le symptôme de `start-dev`, qui ignore la base "
        "déclarée et embarque la sienne, en fichier, dans le conteneur."
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
    assert not manquants, (
        f"Comptes de l'annuaire absents du realm : {sorted(manquants)}. "
        f"Présents : {sorted(presents)}. La fédération est-elle déclarée, et "
        "la synchronisation a-t-elle été DEMANDÉE ?"
    )

    jetons = _jeton_utilisateur(idp, cahier)
    assert "access_token" in jetons, (
        f"« {cahier['UTILISATEUR']} » ne se connecte pas à travers le "
        f"fournisseur : {json.dumps(jetons)[:250]}. Les comptes sont présents "
        "mais l'authentification ne remonte pas à l'annuaire : l'adresse de "
        "connexion de la fédération est-elle joignable DEPUIS LE CONTENEUR ?"
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
    assert devops in par_nom, (
        f"Le groupe « {devops} » de l'annuaire n'est pas dans le realm : "
        f"{sorted(par_nom)}. Le mappeur de groupes est-il déclaré, et la "
        "synchronisation du mappeur demandée ?"
    )

    membres = _api(idp, cahier, jeton,
                   f"realms/{realm}/groups/{par_nom[devops]['id']}"
                   "/members?max=200")
    noms = sorted(m.get("username") for m in membres)

    # LE COMPTE QUI RESTE, et non la liste d'origine : cette épreuve demande
    # aussi de traiter le départ de `QUI_PART`, qui était membre de ce groupe.
    # Exiger la liste d'avant ferait échouer ce test sur le travail que le test
    # du départ exige, et les deux se contrediraient.
    reste = cahier["COMPTE_CONCERNE"]
    assert reste in noms, (
        f"Le groupe « {devops} » porte {noms}, sans « {reste} ». Un groupe "
        "importé mais vide est le signe que le mappeur lit l'appartenance dans "
        "le mauvais attribut."
    )
    assert cahier["QUI_PART"] not in noms, (
        f"Le groupe « {devops} » porte encore « {cahier['QUI_PART']} », dont "
        "le départ est à traiter. Son appartenance se retire à la SOURCE, dans "
        "l'annuaire, puis se resynchronise."
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

    assert client.get("publicClient") is True, (
        f"« {cahier['CLIENT_APPLI_ATTENDU']} » n'est pas public. Une "
        "application qui tourne chez l'usager ne garde aucun secret."
    )
    assert client.get("standardFlowEnabled") is True, (
        "Le flux de code d'autorisation est fermé : l'application ne peut pas "
        "faire authentifier qui que ce soit."
    )
    assert client.get("implicitFlowEnabled") is False, (
        "Le flux implicite est ouvert. Il rend le jeton dans l'URL, où il "
        "finit dans l'historique et les journaux du serveur, et la RFC 9700 le "
        "proscrit."
    )
    assert client.get("directAccessGrantsEnabled") is False, (
        "L'octroi direct par mot de passe est ouvert sur l'application. Il est "
        "ACTIF PAR DÉFAUT : le fermer est un geste explicite, et le laisser "
        "fait passer le mot de passe de l'usager par l'application."
    )
    assert client.get("attributes", {}).get(
        "pkce.code.challenge.method") == "S256", (
        "PKCE S256 n'est pas exigé. Sans lui, un code d'autorisation "
        "intercepté sur le poste suffit à obtenir un jeton."
    )
    jokers = [u for u in client.get("redirectUris") or [] if u.endswith("/*")
              or u == "*"]
    assert not jokers, (
        f"Des URI de redirection portent un joker : {jokers}. Une redirection "
        "trop large laisse envoyer le code d'autorisation ailleurs."
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
    assert etat.rc == 0 and etat.stdout.strip(), (
        "L'application témoin ne répond pas sur son port "
        f"{cahier['PORT_APPLI_TEMOIN']} : elle n'a pas été démarrée."
    )
    try:
        config = json.loads(etat.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"L'état du témoin n'est pas du JSON : "
                    f"{etat.stdout[:200]!r}")
    assert config.get("configuration_lue"), (
        f"L'application témoin ne lit aucune configuration : "
        f"{json.dumps(config)[:200]}"
    )
    attendu = (f"{cahier['URL_KEYCLOAK_ATTENDUE']}/realms/"
               f"{cahier['REALM_ATTENDU']}")
    assert config.get("issuer") == attendu, (
        f"L'application pointe sur l'issuer « {config.get('issuer')} » et non "
        f"« {attendu} ». Une application de notes n'authentifie pas les "
        "administrateurs du serveur."
    )

    res = idp.run(
        "timeout 90 python3 -I /opt/iam-lab/outils/parcours.py "
        f"--depart {shlex.quote(depart)} "
        f"--utilisateur {shlex.quote(cahier['UTILISATEUR'])} "
        f"--mot-de-passe {shlex.quote(cahier['MOT_DE_PASSE'])}")
    assert res.rc != 2, (
        "Le témoin de parcours n'a pas pu mesurer, ce qui n'est pas la même "
        f"chose qu'une intégration cassée :\n{res.stdout}{res.stderr}"
    )
    try:
        parcours = json.loads(res.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"Le témoin n'a rendu aucun JSON :\n{res.stdout[:400]}")

    assert parcours["connexion_posee"], (
        "Le parcours n'a jamais rencontré le formulaire de connexion du "
        "fournisseur : l'application ne délègue pas l'authentification.\n"
        f"étapes : {json.dumps(parcours['etapes'])}"
    )
    assert parcours["http"] == 200, (
        f"Le parcours finit sur HTTP {parcours['http']} à "
        f"{parcours['arrivee']}."
    )
    assert cahier["UTILISATEUR"] in parcours.get("texte", ""), (
        "L'application ne montre pas le nom de la personne connectée à "
        f"l'arrivée ({parcours['arrivee']}). Le jeton est-il validé et lu ?"
    )


# ── Lab 05 : l'API fermée ───────────────────────────────────────────────────


def test_l_api_refuse_sans_jeton_et_accepte_avec_le_bon(idp):
    """401 sans jeton, 200 avec un jeton qui porte l'audience et le scope."""
    cahier = _cahier(idp)
    url = f"http://127.0.0.1:{cahier['PORT_API']}/notes"

    sans = idp.run(
        f"curl -sS --max-time 10 -o /dev/null -w '%{{http_code}}' {url}")
    assert sans.stdout.strip() == "401", (
        f"L'API répond HTTP {sans.stdout.strip()} sans aucun jeton, au lieu "
        "de 401. Une API qui sert des données sans savoir à qui est le défaut "
        "que cette épreuve existe pour fermer."
    )

    jetons = _jeton_utilisateur(idp, cahier, scope=cahier["SCOPE_LECTURE"])
    assert "access_token" in jetons, (
        f"Pas de jeton avec le scope « {cahier['SCOPE_LECTURE']} » : "
        f"{json.dumps(jetons)[:250]}. Le scope existe-t-il, et est-il attaché "
        "au client de test ?"
    )
    avec = idp.run(
        f"curl -sS --max-time 10 -o /dev/null -w '%{{http_code}}' {url} "
        f"-H {shlex.quote('Authorization: Bearer ' + jetons['access_token'])}")
    assert avec.stdout.strip() == "200", (
        f"L'API répond HTTP {avec.stdout.strip()} avec un jeton pourtant "
        "porteur du scope de lecture. Vérifie-t-elle la bonne audience, et le "
        "mappeur d'audience est-il posé sur le scope ?"
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
    assert "access_token" in jetons, "Pas de jeton de lecture."

    ecriture = idp.run(
        f"curl -sS --max-time 10 -o /dev/null -w '%{{http_code}}' -X POST "
        f"{url} -H {shlex.quote('Authorization: Bearer ' + jetons['access_token'])} "
        "-H 'Content-Type: application/json' -d '{}'")
    assert ecriture.stdout.strip() == "403", (
        f"Une écriture avec un jeton de LECTURE répond HTTP "
        f"{ecriture.stdout.strip()} au lieu de 403. Si c'est 200, le scope "
        "n'est pas vérifié ; si c'est 401, l'API confond « je ne vous connais "
        "pas » et « cela ne suffit pas »."
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
    assert "access_token" in jetons, (
        f"Pas de jeton avec le scope « {cahier['SCOPE_AUTRE_API']} » : ce "
        "test a besoin d'un jeton destiné à une AUTRE application pour "
        f"mesurer quoi que ce soit. {json.dumps(jetons)[:200]}"
    )
    res = idp.run(
        f"curl -sS --max-time 10 -o /dev/null -w '%{{http_code}}' {url} "
        f"-H {shlex.quote('Authorization: Bearer ' + jetons['access_token'])}")
    assert res.stdout.strip() == "401", (
        f"L'API accepte (HTTP {res.stdout.strip()}) un jeton destiné à une "
        "autre application. Elle ne vérifie pas `aud`, et n'importe quelle "
        "application du realm peut lui parler."
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

    assert service.get("serviceAccountsEnabled") is True, (
        f"« {cahier['CLIENT_SERVICE_ATTENDU']} » n'a pas de compte de "
        "service : il ne peut pas s'authentifier sans personne."
    )
    assert service.get("publicClient") is False, (
        "Un service qui s'authentifie seul doit être confidentiel : sans "
        "secret, n'importe qui peut se présenter en son nom."
    )

    secret = _api(idp, cahier, jeton,
                  f"realms/{cahier['REALM_ATTENDU']}/clients/"
                  f"{service['id']}/client-secret")
    assert isinstance(secret, dict) and secret.get("value"), (
        f"Le service n'a pas de secret : {json.dumps(secret)[:200]}"
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
        pytest.fail(f"Pas de JSON au point de jeton : {jetons.stdout[:200]!r}")
    assert "access_token" in charge, (
        f"Le service n'obtient pas de jeton : {json.dumps(charge)[:250]}"
    )

    url = f"http://127.0.0.1:{cahier['PORT_API']}/notes"
    entete = shlex.quote("Authorization: Bearer " + charge["access_token"])
    lecture = idp.run(
        f"curl -sS --max-time 10 -o /dev/null -w '%{{http_code}}' {url} "
        f"-H {entete}")
    assert lecture.stdout.strip() == "200", (
        f"Le service ne lit pas l'API (HTTP {lecture.stdout.strip()}). En "
        "client credentials, seuls les scopes PAR DÉFAUT arrivent dans le "
        "jeton : le scope de lecture est-il attaché par défaut à ce client ?"
    )
    ecriture = idp.run(
        f"curl -sS --max-time 10 -o /dev/null -w '%{{http_code}}' -X POST "
        f"{url} -H {entete} -H 'Content-Type: application/json' -d '{{}}'")
    assert ecriture.stdout.strip() == "403", (
        f"Le service ÉCRIT dans l'API (HTTP {ecriture.stdout.strip()}). Un "
        "service de sauvegarde lit. Un accès machine trop large est plus "
        "dangereux qu'un accès humain, parce que personne ne le surveille."
    )


# ── Lab 07 : l'authentification forte, imposée à un groupe ──────────────────


def test_le_second_facteur_est_impose_par_le_groupe_et_non_par_compte(idp):
    """Un rôle attaché AU GROUPE, une condition de rôle, et pas de condition
    « seulement ceux qui en ont déjà un ».

    L'exigence doit suivre l'appartenance : attachée compte par compte, elle
    oublie le prochain arrivant, et personne ne s'en aperçoit avant l'audit.
    """
    cahier = _cahier(idp)
    jeton = _jeton_admin(idp, cahier)
    realm = cahier["REALM_ATTENDU"]
    sensible = cahier["GROUPE_SENSIBLE"]

    le_realm = _api(idp, cahier, jeton, f"realms/{realm}", brut=True)
    assert le_realm.strip().startswith("{"), (
        f"Le realm « {realm} » ne répond pas : {le_realm[:200]!r}"
    )
    flux_navigateur = json.loads(le_realm).get("browserFlow", "")
    assert flux_navigateur != "browser", (
        "Le realm utilise encore le flux de navigateur fourni. L'exigence "
        "doit vivre dans une COPIE, qu'on active : un flux fourni modifié ne "
        "se restaure pas, et c'est le filet qui permet de revenir quand une "
        "exigence enferme tout le monde dehors."
    )

    groupes = _api(idp, cahier, jeton, f"realms/{realm}/groups?max=200")
    par_nom = {g.get("name"): g for g in groupes}
    assert sensible in par_nom, (
        f"Le groupe « {sensible} » n'est pas dans le realm : {sorted(par_nom)}"
    )
    roles_du_groupe = _api(
        idp, cahier, jeton,
        f"realms/{realm}/groups/{par_nom[sensible]['id']}/role-mappings/realm")
    noms = {r.get("name") for r in roles_du_groupe}
    assert noms, (
        f"Aucun rôle n'est attaché au groupe « {sensible} ». L'exigence doit "
        "suivre l'appartenance, et c'est un rôle attaché au groupe qui le "
        "permet : attachée compte par compte, elle oublie le prochain qui "
        "arrive."
    )

    executions = _api(idp, cahier, jeton,
                      f"realms/{realm}/authentication/flows/"
                      f"{flux_navigateur.replace(' ', '%20')}/executions")
    assert isinstance(executions, list), (
        f"Les exécutions du flux « {flux_navigateur} » ne se lisent pas : "
        f"{json.dumps(executions)[:200]}"
    )
    fournisseurs = {e.get("providerId"): e for e in executions
                    if e.get("providerId")}

    assert "conditional-user-role" in fournisseurs, (
        "Le flux ne porte aucune condition de rôle. Sans elle, l'exigence "
        "s'applique à tout le monde, ce qui enferme aussi les administrateurs, "
        "ou à personne."
    )
    condition = fournisseurs["conditional-user-role"]
    assert condition.get("requirement") == "REQUIRED", (
        f"La condition de rôle est en « {condition.get('requirement')} » et "
        "non REQUIRED : elle ne filtre rien."
    )
    assert condition.get("authenticationConfig"), (
        "La condition de rôle n'est pas CONFIGURÉE : elle existe, elle est "
        "obligatoire, et elle ne nomme aucun rôle. Il faut lui dire lequel."
    )

    otp = fournisseurs.get("auth-otp-form", {})
    assert otp.get("requirement") == "REQUIRED", (
        f"L'étape de second facteur est en « {otp.get('requirement')} » et non "
        "REQUIRED : les comptes concernés peuvent s'en passer."
    )
    # DANS LE SOUS-FLUX DU SECOND FACTEUR, et non dans le flux entier.
    #
    # Une copie du flux de navigateur porte DEUX `conditional-user-configured` :
    # une dans le sous-flux du second facteur, une dans celui des
    # organisations. Celle qui compte est la première, et chercher dans le flux
    # entier verrait la seconde, qui n'a rien à voir.
    sous_flux = [e.get("displayName") for e in executions
                 if e.get("displayName")
                 and "Conditional 2FA" in e.get("displayName", "")]
    assert sous_flux, (
        "Le flux ne porte aucun sous-flux de second facteur conditionnel : "
        f"{[e.get('displayName') for e in executions]}"
    )
    du_sous_flux = _api(
        idp, cahier, jeton,
        f"realms/{realm}/authentication/flows/"
        f"{sous_flux[0].replace(' ', '%20')}/executions")
    assert isinstance(du_sous_flux, list), (
        f"Les exécutions du sous-flux « {sous_flux[0]} » ne se lisent pas : "
        f"{json.dumps(du_sous_flux)[:200]}"
    )
    dedans = {e.get("providerId") for e in du_sous_flux if e.get("providerId")}
    assert "conditional-user-configured" not in dedans, (
        "Le sous-flux du second facteur porte encore "
        "`conditional-user-configured`. Mesuré : avec elle, un compte SANS "
        "second facteur se connecte directement, même avec l'étape OTP en "
        "REQUIRED. L'exigence n'est alors imposée à personne, et la console "
        "paraît juste."
    )


def test_les_deux_parcours_se_terminent_differemment(idp):
    """Le compte concerné est ARRÊTÉ, le compte épargné ENTRE.

    Si les deux passent, l'exigence ne s'applique à personne. Si les deux sont
    arrêtés, elle s'applique à tout le monde, et la prochaine personne enfermée
    dehors sera l'administrateur.
    """
    cahier = _cahier(idp)
    depart = f"http://127.0.0.1:{cahier['PORT_APPLI_TEMOIN']}/connexion"

    resultats = {}
    for role, compte in (("épargné", cahier["COMPTE_EPARGNE"]),
                         ("concerné", cahier["COMPTE_CONCERNE"])):
        idp.run(
            f"curl -sS --max-time 10 "
            f"http://127.0.0.1:{cahier['PORT_APPLI_TEMOIN']}/deconnexion")
        res = idp.run(
            "timeout 90 python3 -I /opt/iam-lab/outils/parcours.py "
            f"--depart {shlex.quote(depart)} "
            f"--utilisateur {shlex.quote(compte)} "
            f"--mot-de-passe {shlex.quote(cahier['MOT_DE_PASSE'])} "
            f"--attendre-texte {shlex.quote('Connecté en tant que ' + compte)} "
            "--tours 25")
        assert res.rc != 2, (
            f"Le témoin n'a pas pu mesurer le parcours de {compte} :\n"
            f"{res.stdout}{res.stderr}")
        try:
            resultats[role] = json.loads(res.stdout)
        except json.JSONDecodeError:
            pytest.fail(f"Le témoin n'a rendu aucun JSON pour {compte} :\n"
                        f"{res.stdout[:300]}")

    assert resultats["épargné"].get("texte_trouve"), (
        f"Le compte épargné « {cahier['COMPTE_EPARGNE']} » n'arrive pas à se "
        "connecter : l'exigence s'applique à tout le monde, et non au seul "
        f"groupe « {cahier['GROUPE_SENSIBLE']} ». Arrivée : "
        f"{resultats['épargné'].get('arrivee')}"
    )
    assert not resultats["concerné"].get("texte_trouve"), (
        f"Le compte concerné « {cahier['COMPTE_CONCERNE']} » entre sans second "
        "facteur. L'exigence n'est imposée à personne : la condition de rôle "
        "est-elle configurée sur le bon rôle, et le sous-flux porte-t-il "
        "encore `conditional-user-configured` ?"
    )


def test_la_politique_de_mot_de_passe_mise_sur_la_longueur(idp):
    """Longueur d'abord, et pas de règles de composition.

    NIST SP 800-63B demande de la longueur et proscrit les règles de
    composition et l'expiration arbitraire : elles produisent des mots de passe
    prévisibles, écrits sur un papier.
    """
    cahier = _cahier(idp)
    jeton = _jeton_admin(idp, cahier)
    brut = _api(idp, cahier, jeton, f"realms/{cahier['REALM_ATTENDU']}",
                brut=True)
    politique = json.loads(brut).get("passwordPolicy") or ""

    assert "length(" in politique, (
        f"Aucune longueur minimale dans la politique : {politique!r}. C'est la "
        "seule exigence qui fait réellement travailler une attaque."
    )
    longueur = int(politique.split("length(")[1].split(")")[0])
    assert longueur >= 12, (
        f"La longueur minimale est de {longueur} caractères. Douze est le "
        "plancher raisonnable aujourd'hui."
    )
    interdites = [r for r in ("upperCase", "lowerCase", "digits",
                              "specialChars", "forceExpiredPasswordChange")
                  if r in politique]
    assert not interdites, (
        f"La politique impose {interdites}, c'est-à-dire des règles de "
        "composition ou une expiration. Elles produisent « Printemps2026! » "
        "et un papier sous le clavier."
    )


# ── Lab 08 : le départ, traité jusqu'au bout ────────────────────────────────


def test_le_depart_est_traite_jusqu_au_bout(idp):
    """Désactivé, sans aucun groupe, et sans aucune session.

    Trois gestes, et deux d'entre eux répondent « fait » sans avoir fait :
    désactiver ne ferme pas les sessions, et retirer une appartenance fédérée
    est refusé par le fournisseur quand le mappeur est en lecture seule.
    """
    cahier = _cahier(idp)
    jeton = _jeton_admin(idp, cahier)
    realm = cahier["REALM_ATTENDU"]
    qui = cahier["QUI_PART"]

    trouves = _api(idp, cahier, jeton,
                   f"realms/{realm}/users?username={qui}&exact=true")
    assert isinstance(trouves, list) and trouves, (
        f"Le compte « {qui} » n'existe pas dans le realm : il devait y arriver "
        "par la fédération."
    )
    compte = trouves[0]

    assert compte.get("enabled") is False, (
        f"« {qui} » est encore actif. C'est le premier geste d'un départ."
    )

    groupes = _api(idp, cahier, jeton,
                   f"realms/{realm}/users/{compte['id']}/groups")
    assert groupes == [], (
        f"« {qui} » appartient encore à {[g.get('name') for g in groupes]}. "
        "Le fournisseur REFUSE de retirer une appartenance fédérée quand le "
        "mappeur est en lecture seule : elle se retire à la SOURCE, puis se "
        "resynchronise, et le cache des comptes fédérés doit être vidé."
    )

    sessions = _api(idp, cahier, jeton,
                    f"realms/{realm}/users/{compte['id']}/sessions")
    assert sessions == [], (
        f"« {qui} » a encore {len(sessions)} session(s) ouverte(s). Désactiver "
        "un compte NE FERME PAS ses sessions : un jeton déjà émis continue "
        "d'ouvrir les portes jusqu'à son expiration."
    )


def test_la_revue_des_acces_est_complete_et_a_jour(idp):
    """Un fichier qui décrit l'état APRÈS le travail, comptes, groupes et rôles.

    Une revue écrite avant le départ décrit un monde qui n'existe plus, et
    c'est pourtant l'ordre dans lequel on la produit d'habitude.
    """
    cahier = _cahier(idp)
    jeton = _jeton_admin(idp, cahier)
    realm = cahier["REALM_ATTENDU"]

    fichier = idp.file(cahier["FICHIER_DE_REVUE"])
    assert fichier.exists, (
        f"{cahier['FICHIER_DE_REVUE']} est absent : la revue des accès n'a pas "
        "été produite."
    )
    try:
        revue = json.loads(fichier.content_string)
    except json.JSONDecodeError:
        pytest.fail(
            f"{cahier['FICHIER_DE_REVUE']} n'est pas du JSON lisible : "
            f"{fichier.content_string[:200]!r}")

    entrees = revue.get("comptes") if isinstance(revue, dict) else revue
    assert isinstance(entrees, list) and entrees, (
        f"La revue ne porte aucune liste de comptes : "
        f"{json.dumps(revue)[:200]}"
    )

    par_nom = {}
    for entree in entrees:
        assert isinstance(entree, dict) and entree.get("username"), (
            f"Une entrée de la revue n'a pas de `username` : {entree}"
        )
        clefs = set(entree)
        assert any(k in clefs for k in ("groupes", "groups")), (
            f"L'entrée de « {entree['username']} » ne porte pas ses groupes : "
            f"{sorted(clefs)}"
        )
        assert any(k in clefs for k in ("roles", "rôles")), (
            f"L'entrée de « {entree['username']} » ne porte pas ses rôles : "
            f"{sorted(clefs)}. Une revue qui ne liste que les groupes ne voit "
            "pas les accès accordés directement, et c'est là qu'ils vivent."
        )
        par_nom[entree["username"]] = entree

    du_realm = _api(idp, cahier, jeton, f"realms/{realm}/users?max=200")
    attendus = {c.get("username") for c in du_realm}
    manquants = attendus - set(par_nom)
    assert not manquants, (
        f"La revue oublie {sorted(manquants)}. Elle doit être complète : un "
        "compte absent de la revue est un accès que personne n'examine."
    )

    qui = cahier["QUI_PART"]
    entree = par_nom.get(qui)
    assert entree is not None, f"La revue ne mentionne pas « {qui} »."
    groupes = entree.get("groupes", entree.get("groups", []))
    assert not groupes, (
        f"La revue montre « {qui} » encore dans {groupes}, alors que son "
        "départ a été traité. Elle a été écrite AVANT le travail, et elle "
        "décrit un monde qui n'existe plus."
    )


# ── Lab 09 : une sauvegarde qui se restaure ─────────────────────────────────


def test_une_sauvegarde_de_la_base_se_restaure_dans_une_base_vide(idp):
    """Une sauvegarde qu'on n'a pas restaurée est une intention.

    Ce test ne lit pas le fichier : il crée une base, y restaure la sauvegarde,
    compte les comptes dedans, et la supprime. Un export de realm ne passerait
    pas, et c'est voulu : il ne porte aucun événement, donc aucune trace de qui
    s'est connecté.
    """
    cahier = _cahier(idp)
    base = "essai_restauration_epreuve"

    trouvees = idp.run(
        f"find {cahier['REPERTOIRE_SAUVEGARDES']} -type f "
        r"\( -name '*.dump' -o -name '*.sql' -o -name '*.sql.gz' "
        r"-o -name '*.custom' \) -printf '%T@ %s %p\n' | sort -n | tail -1")
    assert trouvees.stdout.strip(), (
        f"Aucune sauvegarde dans {cahier['REPERTOIRE_SAUVEGARDES']}. Le test y "
        "cherche un fichier .dump, .sql, .sql.gz ou .custom."
    )
    _, taille, chemin = trouvees.stdout.split(None, 2)
    chemin = chemin.strip()
    assert int(taille) > 10000, (
        f"La sauvegarde {chemin} ne pèse que {taille} octets : une base de "
        "Keycloak avec un realm fédéré en fait quelques centaines de "
        "kilo-octets. Ce fichier est vide, tronqué, ou c'est un export de "
        "realm, qui n'est pas une sauvegarde."
    )

    conteneur = idp.run(
        "docker ps --filter 'name=db' --format '{{.Names}}' | head -n 1")
    nom = conteneur.stdout.strip()
    assert nom, (
        "Aucun conteneur de base de données : le fournisseur tourne-t-il sur "
        "une base externe ?"
    )

    idp.run(f"docker exec {nom} psql -U keycloak -d postgres "
            f"-c 'DROP DATABASE IF EXISTS {base}'")
    creation = idp.run(f"docker exec {nom} psql -U keycloak -d postgres "
                       f"-c 'CREATE DATABASE {base}'")
    assert creation.rc == 0, (
        f"Impossible de créer la base d'essai : {creation.stderr[:200]!r}"
    )

    try:
        if chemin.endswith(".sql.gz"):
            commande = (f"gunzip -c {shlex.quote(chemin)} | docker exec -i "
                        f"{nom} psql -U keycloak -d {base}")
        elif chemin.endswith(".sql"):
            commande = (f"docker exec -i {nom} psql -U keycloak -d {base} "
                        f"< {shlex.quote(chemin)}")
        else:
            commande = (f"docker exec -i {nom} pg_restore -U keycloak "
                        f"-d {base} < {shlex.quote(chemin)}")
        restauration = idp.run(commande)

        tables = idp.run(
            f"docker exec {nom} psql -U keycloak -d {base} -tAc "
            "\"select count(*) from information_schema.tables "
            "where table_schema='public'\"").stdout.strip()
        assert tables.isdigit() and int(tables) > 50, (
            f"La restauration de {chemin} n'a produit que {tables!r} tables.\n"
            f"{restauration.stdout[-300:]}{restauration.stderr[-300:]}"
        )

        comptes = idp.run(
            f"docker exec {nom} psql -U keycloak -d {base} -tAc "
            "\"select count(*) from user_entity where realm_id in "
            f"(select id from realm where name='{cahier['REALM_ATTENDU']}')\""
        ).stdout.strip()
        assert comptes.isdigit() and int(comptes) >= 3, (
            f"La base restaurée ne porte que {comptes!r} comptes du realm "
            f"« {cahier['REALM_ATTENDU']} », au lieu des trois de l'annuaire. "
            "La sauvegarde a-t-elle été prise après la fédération ?"
        )
    finally:
        # La base d'essai part, quoi qu'il arrive : un test qui laisse des
        # traces fait échouer le suivant pour une raison qui n'est pas la
        # sienne.
        idp.run(f"docker exec {nom} psql -U keycloak -d postgres "
                f"-c 'DROP DATABASE IF EXISTS {base}'")
