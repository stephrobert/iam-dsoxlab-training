"""Ce qu'un compte externe obtient, et ce qu'il ne doit pas obtenir.

Aucun test ne lit la configuration pour la juger bonne. Ils jouent une
connexion réelle avec un compte que le realm ne détient pas, puis ils lisent le
compte qui en résulte : son rattachement, son groupe, et surtout ses rôles.

DEUX PARCOURS, DEUX RÉSULTATS ATTENDUS OPPOSÉS

Le partenaire a deux comptes, et c'est le sujet du lab :

    dora   son adresse ne correspond à personne   la connexion DOIT aboutir
    bob    son adresse est celle d'un compte local le flux DOIT s'arrêter

Le second est la preuve POSITIVE qu'aucune liaison aveugle n'a lieu, ce qui
vaut mieux que de lire un réglage. Si la connexion de `bob` aboutissait, un
inconnu viendrait de prendre le contrôle d'un compte interne, en silence.

Le flux par défaut de Keycloak s'en protège : mesuré le 2026-10-16, il enchaîne
`Create User If Unique`, puis `Confirm link existing account` et une
vérification par courriel ou par ré-authentification. Un flux qui emploierait
`idp-auto-link` sauterait tout cela.

CE QUE LA MESURE A DONNÉ POUR UN COMPTE LIÉ SAIN

    liens   : ['oidc-partenaire']
    groupes : ['partenaires']
    roles   : realm=['default-roles-formation'] clients={}

Aucun rôle d'administration, et c'est ce que le dernier test vérifie.
"""

from __future__ import annotations

import json
import urllib.parse

import pytest

from conftest import lab_host, lab_target_host

# L'hôte RÉELLEMENT testé. `dsoxlab check --target` peut en imposer un autre,
# et coder le nom en dur ferait tester la cible par défaut en prétendant tester
# celle qu'on a demandée.
CIBLE = lab_target_host("idp.lab")

KEYCLOAK = "http://127.0.0.1:8080"
COURTIER = "formation"
PARTENAIRE = "entreprise-externe"
ALIAS = "oidc-partenaire"
PORT_TEMOIN = 9080
OUTILS = "/opt/iam-lab/outils"
IDENTIFIANTS = "/opt/iam-lab/identifiants-lab.txt"
SECRETS_DU_SOCLE = "/opt/socle-iam/.env"

#: Les rôles qu'un compte venu de l'extérieur ne doit jamais porter.
ROLES_INTERDITS = {
    "admin", "realm-admin", "create-realm", "manage-users", "manage-realm",
    "manage-clients", "manage-identity-providers", "manage-authorization",
    "impersonation",
}

#: Les exécutions de flux qui lient un compte externe SANS vérification.
LIAISON_AVEUGLE = {"idp-auto-link"}


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


def _fournisseur(hote) -> dict:
    trouves = _api(hote, f"realms/{COURTIER}/identity-provider/instances") or []
    assert trouves, (
        f"Aucun fournisseur d'identité dans le realm « {COURTIER} ». C'est le "
        "premier geste du challenge : le courtier doit savoir à qui déléguer."
    )
    alias = {i.get("alias") for i in trouves}
    assert ALIAS in alias, (
        f"Aucun fournisseur d'alias « {ALIAS} » (trouvés : {sorted(alias)}). "
        "L'alias décide de l'adresse de retour, que le partenaire a déjà "
        "déclarée chez lui : en changer fait refuser la connexion."
    )
    return next(i for i in trouves if i.get("alias") == ALIAS)


def _config(objet: dict, clef: str) -> str:
    valeur = (objet.get("config") or {}).get(clef)
    if isinstance(valeur, list):
        return valeur[0] if valeur else ""
    return valeur or ""


def _compte_du_courtier(hote, nom: str) -> dict | None:
    trouves = _api(hote, f"realms/{COURTIER}/users?username={nom}&exact=true") or []
    if not trouves:
        return None
    return _api(hote, f"realms/{COURTIER}/users/{trouves[0]['id']}")


def _parcours(hote, qui: str) -> dict:
    """Le parcours d'un compte du partenaire, jusqu'où il va.

    L'application témoin garde l'état de la dernière connexion en mémoire : on
    la déconnecte d'abord, sinon un parcours qui échoue laisserait la page du
    précédent et le test lirait un succès qui n'est pas le sien.
    """
    identifiants = _identifiants(hote)
    hote.run(f"curl -sS --max-time 10 http://127.0.0.1:{PORT_TEMOIN}/deconnexion")
    attendu = f"Connecté en tant que {qui}"
    res = hote.run(
        f"python3 {OUTILS}/parcours.py "
        f"--depart http://127.0.0.1:{PORT_TEMOIN}/connexion "
        f"--utilisateur {qui} "
        f"--mot-de-passe {identifiants['MOT_DE_PASSE_EXTERNE']!r} "
        f"--attendre-texte {attendu!r} --tours 25"
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


# ── Les tests ────────────────────────────────────────────────────────────────


def test_le_fournisseur_externe_est_declare_et_actif(idp):
    """Déclaré, activé, et pointé sur le bon partenaire.

    Vert avant le travail ? Non : le setup vérifie que le courtier n'a aucun
    fournisseur d'identité, et refuse de poser la situation sinon.
    """
    fournisseur = _fournisseur(idp)

    assert fournisseur.get("enabled") is True, (
        "Le fournisseur d'identité est déclaré mais désactivé : il n'apparaîtra "
        "pas et personne ne pourra s'en servir."
    )
    assert fournisseur.get("providerId") == "oidc", (
        f"Le fournisseur est de type « {fournisseur.get('providerId')} ». Le "
        "partenaire publie un document de découverte OIDC, pas des "
        "métadonnées SAML."
    )

    emetteur_attendu = f"{KEYCLOAK}/realms/{PARTENAIRE}"
    lu = _config(fournisseur, "issuer")
    assert lu == emetteur_attendu, (
        f"Le fournisseur attend des jetons de « {lu or 'aucun émetteur'} » au "
        f"lieu de « {emetteur_attendu} ». Sans émetteur déclaré, rien ne "
        "vérifie d'où vient le jeton."
    )
    assert _config(fournisseur, "validateSignature") == "true", (
        "La signature des jetons du partenaire n'est pas vérifiée "
        f"(validateSignature = {_config(fournisseur, 'validateSignature')!r})."
    )

    assert fournisseur.get("linkOnly") is not True, (
        "Le fournisseur est en « lien seulement » : il ne pourra pas créer de "
        "compte, et un utilisateur du partenaire qui n'a pas déjà un compte "
        "local ne pourra pas entrer."
    )


def test_le_flux_de_premier_login_ne_lie_personne_a_l_aveugle(idp):
    """LE TEST QUI COMPTE LE PLUS, et son piège est posé par le setup.

    Vert avant le travail ? Non : sans fournisseur d'identité, il n'y a pas de
    flux de premier login à examiner.

    Le realm courtier contient `chloe`, un compte local qui porte la MÊME
    adresse que le compte externe. Un flux qui lie automatiquement sur l'adresse
    donne à l'inconnu le contrôle de ce compte, sans que personne n'ait rien à
    faire et sans qu'aucune trace ne le signale comme anormal.
    """
    fournisseur = _fournisseur(idp)
    flux = fournisseur.get("firstBrokerLoginFlowAlias")
    assert flux, (
        "Le fournisseur ne désigne aucun flux de premier login. Keycloak en "
        "fournit un qui demande confirmation avant de lier : il faut le "
        "nommer."
    )

    executions = _api(
        idp,
        f"realms/{COURTIER}/authentication/flows/"
        f"{urllib.parse.quote(flux)}/executions",
    ) or []
    actives = {
        e.get("providerId")
        for e in executions
        if e.get("requirement") in {"REQUIRED", "ALTERNATIVE"}
    }

    fautives = actives & LIAISON_AVEUGLE
    assert not fautives, (
        f"Le flux « {flux} » emploie {sorted(fautives)}, qui lie un compte "
        "externe à un compte local SANS vérification. Le realm contient un "
        "compte de même adresse que le compte externe : avec ce flux, "
        "l'inconnu en prend le contrôle.\n"
        f"Exécutions actives : {sorted(a for a in actives if a)}"
    )

    assert "idp-confirm-link" in actives or "idp-create-user-if-unique" in actives, (
        f"Le flux « {flux} » ne contient ni création d'un compte unique ni "
        "confirmation de liaison. Il ne protège donc pas d'une adresse qui "
        f"correspond par hasard. Exécutions actives : "
        f"{sorted(a for a in actives if a)}"
    )


def test_un_compte_externe_se_connecte_vraiment(idp):
    """Le parcours entier, avec un compte que le realm ne détient pas.

    Vert avant le travail ? Non : sans fournisseur, le parcours s'arrête sur la
    page de connexion du courtier, où ce compte n'existe pas.

    C'est `dora` qui est jouée ici, et non `bob` : l'adresse de `dora` ne
    correspond à personne dans le courtier, donc sa connexion doit aboutir sans
    rien demander. Le cas de `bob` est l'objet d'un test à part.
    """
    etat = idp.run(f"curl -sS --max-time 10 http://127.0.0.1:{PORT_TEMOIN}/etat")
    assert etat.rc == 0 and etat.stdout.strip(), (
        f"L'application témoin ne répond pas sur le port {PORT_TEMOIN}. Le "
        "setup la démarre : son journal est dans "
        "/opt/iam-lab/appli-temoin/temoin.log."
    )

    resultat = _parcours(idp, _identifiants(idp)["UTILISATEUR_QUI_ENTRE"])

    assert resultat.get("connexion_posee") is True, (
        "Le parcours n'a jamais rencontré de formulaire de connexion : "
        f"il s'est arrêté sur {resultat.get('arrivee')}."
    )
    assert resultat.get("texte_trouve") is True, (
        "La page d'arrivée n'affiche pas l'utilisateur connecté. Le parcours "
        f"s'est terminé sur {resultat.get('arrivee')} "
        f"(HTTP {resultat.get('http')}) avec : "
        f"{str(resultat.get('texte'))[:300]}\n\n"
        "Si vous lisez une demande de complément de profil, les mappeurs ne "
        "transmettent pas tout ce que le courtier exige pour créer le compte."
    )


def test_le_compte_arrive_rattache_au_fournisseur(idp):
    """Rattaché, et non recréé à la main.

    Vert avant le travail ? Non : le compte n'existe pas avant la connexion.

    Un compte rattaché suit le partenaire. Un compte créé à la main qui porte
    le même nom ne suit rien, et son mot de passe vit chez vous, ce que toute
    cette fédération existe pour éviter.
    """
    qui = _identifiants(idp)["UTILISATEUR_QUI_ENTRE"]
    compte = _compte_du_courtier(idp, qui)
    assert compte, (
        f"Le realm « {COURTIER} » n'a aucun compte « {qui} ». Le parcours "
        "a-t-il abouti ? Voir le test précédent."
    )

    liens = _api(
        idp, f"realms/{COURTIER}/users/{compte['id']}/federated-identity"
    ) or []
    alias = {li.get("identityProvider") for li in liens}
    assert ALIAS in alias, (
        f"Le compte n'est pas rattaché au fournisseur « {ALIAS} » "
        f"(liens : {sorted(a for a in alias if a)})."
    )
    assert compte.get("email") == f"{qui}@partenaire.example", (
        f"Le compte porte l'adresse {compte.get('email')!r} au lieu de celle "
        "du compte externe. Les mappeurs du fournisseur la transmettent-ils ?"
    )


def test_le_compte_externe_arrive_dans_le_groupe_par_defaut(idp):
    """Un groupe par défaut donne un socle de droits, et un seul endroit à auditer.

    Vert avant le travail ? Non : le nettoyage vérifie qu'aucun groupe par
    défaut ne subsiste.

    Sans groupe par défaut, chaque compte venu de l'extérieur arrive sans rien,
    et quelqu'un lui accorde des droits à la main. Ce « quelqu'un » est la
    raison pour laquelle les revues d'accès trouvent toujours des surprises.
    """
    identifiants = _identifiants(idp)
    attendu = identifiants["GROUPE_ATTENDU"]

    defauts = _api(idp, f"realms/{COURTIER}/default-groups") or []
    noms_defauts = {g["name"] for g in defauts}
    assert attendu in noms_defauts, (
        f"Le realm ne déclare pas « {attendu} » comme groupe par défaut "
        f"(déclarés : {sorted(noms_defauts)}). Le groupe doit exister ET être "
        "désigné comme groupe par défaut du realm : le créer ne suffit pas."
    )

    qui = _identifiants(idp)["UTILISATEUR_QUI_ENTRE"]
    compte = _compte_du_courtier(idp, qui)
    assert compte, f"Le realm « {COURTIER} » n'a aucun compte « {qui} »."
    groupes = _api(idp, f"realms/{COURTIER}/users/{compte['id']}/groups") or []
    noms = {g["name"] for g in groupes}
    assert attendu in noms, (
        f"Le compte externe n'est pas dans « {attendu} » (groupes : "
        f"{sorted(noms)}). Le groupe par défaut s'applique à la CRÉATION du "
        "compte : si vous l'avez déclaré après la première connexion, "
        "supprimez le compte lié et reconnectez-vous."
    )


def test_aucun_role_d_administration_n_est_accorde(idp):
    """Ce que la fédération ne doit PAS donner.

    Vert avant le travail ? Non : le compte n'existe pas.

    C'est le contrôle qu'on oublie, parce que rien ne le réclame. Un compte
    venu d'une autre entreprise qui porte un rôle d'administration est une
    porte ouverte que personne ne regarde, et elle s'ouvre au premier compte
    créé chez le partenaire.
    """
    qui = _identifiants(idp)["UTILISATEUR_QUI_ENTRE"]
    compte = _compte_du_courtier(idp, qui)
    assert compte, f"Le realm « {COURTIER} » n'a aucun compte « {qui} »."

    attributions = _api(
        idp, f"realms/{COURTIER}/users/{compte['id']}/role-mappings"
    ) or {}

    du_realm = {r["name"] for r in attributions.get("realmMappings") or []}
    fautifs = du_realm & ROLES_INTERDITS
    assert not fautifs, (
        f"Le compte externe porte les rôles de realm {sorted(fautifs)}. Un "
        "compte venu d'une autre entreprise ne doit administrer ni le realm ni "
        "ses comptes."
    )

    for nom_client, bloc in (attributions.get("clientMappings") or {}).items():
        roles = {r["name"] for r in bloc.get("mappings") or []}
        fautifs = roles & ROLES_INTERDITS
        assert not fautifs, (
            f"Le compte externe porte {sorted(fautifs)} sur le client "
            f"« {nom_client} ». C'est par là que l'administration de Keycloak "
            "s'accorde, et personne ne regarde jamais ces rôles."
        )


def test_une_adresse_qui_correspond_ne_lie_personne_en_silence(idp):
    """LA PREUVE POSITIVE DU REFUS, et c'est le meilleur test du lab.

    Vert avant le travail ? Non : sans fournisseur d'identité, le parcours
    s'arrête sur la page de connexion du courtier.

    Le setup a posé un compte local qui porte la MÊME adresse que le compte
    externe `bob`. Sa connexion ne doit PAS aboutir : le fournisseur doit
    s'arrêter et demander, parce qu'une adresse qui correspond n'est pas une
    preuve d'identité.

    Mesuré le 2026-10-16, Keycloak rend alors :

        Account already exists
        User with email bob@partenaire.example already exists.
        How do you want to continue?

    Un parcours qui aboutirait ici voudrait dire qu'un inconnu vient de prendre
    le contrôle d'un compte interne, en silence.
    """
    identifiants = _identifiants(idp)
    en_conflit = identifiants["UTILISATEUR_EN_CONFLIT"]
    nom_local = identifiants["COMPTE_LOCAL_PIEGE"]

    resultat = _parcours(idp, en_conflit)

    assert resultat.get("texte_trouve") is not True, (
        f"La connexion de « {en_conflit} » a ABOUTI. Son adresse est celle du "
        f"compte local « {nom_local} » : le fournisseur vient donc de lier un "
        "inconnu à un compte interne sans rien vérifier. C'est une prise de "
        "contrôle de compte, et elle ne laisse aucune trace anormale."
    )

    texte = str(resultat.get("texte") or "").lower()
    assert "already exists" in texte or "existe" in texte, (
        "Le parcours ne s'est pas arrêté sur un écran qui nomme le conflit "
        f"d'adresse. Il s'est terminé sur {resultat.get('arrivee')} avec : "
        f"{str(resultat.get('texte'))[:300]}\n\n"
        "Le flux de premier login doit détecter qu'un compte de même adresse "
        "existe, et demander une vérification au lieu de lier."
    )

    # Et le compte local doit être exactement tel qu'il était.
    trouves = _api(
        idp, f"realms/{COURTIER}/users?username={nom_local}&exact=true"
    ) or []
    assert trouves, (
        f"Le compte local « {nom_local} » a disparu du realm. Un flux de "
        "premier login mal choisi peut le remplacer au lieu de s'arrêter."
    )

    liens = _api(
        idp, f"realms/{COURTIER}/users/{trouves[0]['id']}/federated-identity"
    ) or []
    assert not liens, (
        f"Le compte local « {nom_local} » est désormais rattaché à "
        f"{[li.get('identityProvider') for li in liens]}. L'inconnu du "
        "partenaire en a pris le contrôle, sur la seule foi d'une adresse qui "
        "correspond."
    )
