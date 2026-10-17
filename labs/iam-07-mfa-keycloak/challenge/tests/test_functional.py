"""Deux connexions qui doivent se terminer différemment.

Aucun test ne se contente de lire un réglage. Le cœur du lab est joué : un
compte de l'équipe concernée doit être ARRÊTÉ, un compte épargné doit PASSER,
et les deux ont le même mot de passe et aucun second facteur. C'est leur
appartenance, et rien d'autre, qui doit faire la différence.

TROIS FAITS MESURÉS LE 2026-10-16 QUI DÉCIDENT DE CES TESTS

1. Keycloak 26.8.1 n'a AUCUNE condition de groupe. Les conditions disponibles
   sont `conditional-user-role`, `conditional-user-attribute`,
   `conditional-credential`, `conditional-user-configured`,
   `conditional-client-scope`, `conditional-level-of-authentication` et
   `conditional-sub-flow-executed`. Le ciblage passe donc par un RÔLE, que le
   groupe porte.

2. `conditional-user-configured` est le piège central. Avec lui en place, le
   second facteur n'est exigé que de ceux qui en ont DÉJÀ un : mesuré, un
   compte sans second facteur se connecte directement, même avec l'étape OTP
   en `REQUIRED`. On croit avoir imposé le MFA, et personne ne l'a.

3. Les rôles hérités d'un groupe n'apparaissent PAS dans les rôles directs
   d'un compte. Ils se lisent par `role-mappings/realm/composite`.
"""

from __future__ import annotations

import json
import urllib.parse

import pytest

from conftest import lab_host, lab_target_host, message

# L'hôte RÉELLEMENT testé. `dsoxlab check --target` peut en imposer un autre,
# et coder le nom en dur ferait tester la cible par défaut en prétendant tester
# celle qu'on a demandée.
CIBLE = lab_target_host("idp.lab")

KEYCLOAK = "http://127.0.0.1:8080"
REALM = "formation"
PORT_TEMOIN = 9080
OUTILS = "/opt/iam-lab/outils"
IDENTIFIANTS = "/opt/iam-lab/identifiants-lab.txt"
SECRETS_DU_SOCLE = "/opt/socle-iam/.env"

#: Les règles de composition que NIST SP 800-63B-4 proscrit.
COMPOSITION_PROSCRITE = ("upperCase", "lowerCase", "digits", "specialChars")

#: Les secondes options d'authentification qui résistent au hameçonnage.
RESISTANT_AU_HAMECONNAGE = {"webauthn-authenticator", "webauthn-authenticator-passwordless"}


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


def _le_realm(hote) -> dict:
    realm = _api(hote, f"realms/{REALM}")
    assert isinstance(realm, dict) and realm.get("realm") == REALM, message(
        en=f"The realm \"{REALM}\" cannot be found.",
        fr=f"Le realm « {REALM} » est introuvable.",
    )
    return realm


def _executions(hote, flux: str) -> list[dict]:
    resultat = _api(
        hote,
        f"realms/{REALM}/authentication/flows/"
        f"{urllib.parse.quote(flux)}/executions",
    )
    return resultat if isinstance(resultat, list) else []


def _flux_actif(hote) -> str:
    return _le_realm(hote).get("browserFlow") or ""


def _parcours(hote, qui: str) -> dict:
    identifiants = _identifiants(hote)
    hote.run(f"curl -sS --max-time 10 http://127.0.0.1:{PORT_TEMOIN}/deconnexion")
    attendu = f"Connecté en tant que {qui}"
    res = hote.run(
        f"python3 {OUTILS}/parcours.py "
        f"--depart http://127.0.0.1:{PORT_TEMOIN}/connexion "
        f"--utilisateur {qui} "
        f"--mot-de-passe {identifiants['MOT_DE_PASSE']!r} "
        f"--attendre-texte {attendu!r} --tours 25"
    )
    assert res.rc != 2, message(
        en="The journey tool could not measure, which is not a failure of "
        f"the configuration: {res.stderr.strip()[:400]}",
        fr="L'outil de parcours n'a pas pu mesurer, ce qui n'est pas un échec de "
        f"la configuration : {res.stderr.strip()[:400]}",
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


def test_le_flux_par_defaut_de_keycloak_est_intact(idp):
    """On ne modifie jamais un flux fourni : on le copie.

    Vert avant le travail ? OUI, et c'est le seul test du lab dans ce cas. Il
    n'est pas là pour noter le travail, il est là pour vérifier qu'on n'a pas
    détruit le filet de sécurité : un flux fourni modifié ne se restaure pas
    sans sauvegarde, et c'est le cas d'échec que la fiche nomme.
    """
    executions = _executions(idp, "browser")
    assert executions, message(
        en="The \"browser\" flow cannot be found. If it was deleted, the realm has "
        "no reference flow left and nothing allows going back.",
        fr="Le flux « browser » est introuvable. S'il a été supprimé, le realm n'a "
        "plus de flux de référence et rien ne permet de revenir en arrière.",
    )

    otp = [e for e in executions if e.get("providerId") == "auth-otp-form"]
    assert otp, message(
        en="The \"browser\" flow no longer has its OTP step.",
        fr="Le flux « browser » n'a plus son étape OTP.",
    )
    assert otp[0].get("requirement") == "ALTERNATIVE", message(
        en="The built-in \"browser\" flow was MODIFIED: its OTP step is "
        f"{otp[0].get('requirement')} instead of ALTERNATIVE. A built-in flow is "
        "copied, it is not modified: without it, nothing allows going back "
        "to a known state.",
        fr="Le flux fourni « browser » a été MODIFIÉ : son étape OTP est en "
        f"{otp[0].get('requirement')} au lieu d'ALTERNATIVE. Un flux fourni se "
        "copie, il ne se modifie pas : sans lui, plus rien ne permet de revenir "
        "à un état connu.",
    )
    configuree = [
        e for e in executions
        if e.get("providerId") == "conditional-user-configured"
    ]
    assert configuree, message(
        en="The built-in \"browser\" flow was modified: its "
        "`conditional-user-configured` condition has disappeared.",
        fr="Le flux fourni « browser » a été modifié : sa condition "
        "`conditional-user-configured` a disparu.",
    )


def test_un_flux_copie_est_actif_pour_le_navigateur(idp):
    """Le realm doit employer une copie, pas le flux fourni.

    Vert avant le travail ? Non : le setup remet `browser` comme flux actif et
    supprime tout flux copié.
    """
    actif = _flux_actif(idp)
    assert actif, message(
        en="The realm declares no browser flow.",
        fr="Le realm ne déclare aucun flux de navigateur.",
    )
    assert actif != "browser", message(
        en="The active browser flow is still \"browser\", the one "
        "Keycloak provides. The work asks you to use a copy, to "
        "keep a known state to go back to.",
        fr="Le flux de navigateur actif est encore « browser », celui que "
        "Keycloak fournit. Le travail demande d'en employer une copie, pour "
        "garder un état connu auquel revenir.",
    )

    tous = _api(idp, f"realms/{REALM}/authentication/flows") or []
    le_notre = [f for f in tous if f.get("alias") == actif]
    assert le_notre, message(
        en=f"The active flow \"{actif}\" cannot be found in the realm.",
        fr=f"Le flux actif « {actif} » est introuvable dans le realm.",
    )
    assert le_notre[0].get("builtIn") is False, message(
        en=f"The active flow \"{actif}\" is a flow provided by Keycloak. Use "
        "a copy.",
        fr=f"Le flux actif « {actif} » est un flux fourni par Keycloak. Employez "
        "une copie.",
    )


def test_le_second_facteur_est_conditionne_a_un_role_et_non_a_son_existence(idp):
    """LE PIÈGE DU LAB, et il est silencieux.

    Vert avant le travail ? Non : il n'y a pas de flux copié à examiner.

    Mesuré le 2026-10-16 : avec `conditional-user-configured` dans le sous-flux,
    le second facteur n'est exigé que de ceux qui en ont DÉJÀ un. Un compte sans
    second facteur se connecte directement, même avec l'étape OTP en `REQUIRED`.
    On croit avoir imposé le MFA, et personne ne l'a.

    Et comme Keycloak 26.8.1 n'offre aucune condition de groupe, le ciblage
    passe par `conditional-user-role`.
    """
    actif = _flux_actif(idp)
    executions = _executions(idp, actif)
    assert executions, message(
        en=f"The active flow \"{actif}\" has no execution.",
        fr=f"Le flux actif « {actif} » n'a aucune exécution.",
    )

    # Le sous-flux où vit le second facteur, repéré par l'étape OTP.
    otp = [e for e in executions if e.get("providerId") == "auth-otp-form"]
    assert otp, message(
        en=f"The active flow \"{actif}\" has no OTP step. The second factor "
        "can therefore be required of nobody.",
        fr=f"Le flux actif « {actif} » n'a aucune étape OTP. Le second facteur ne "
        "peut donc être exigé de personne.",
    )
    assert otp[0].get("requirement") in {"REQUIRED", "ALTERNATIVE"}, message(
        en=f"The OTP step is {otp[0].get('requirement')}: it will never be "
        "played.",
        fr=f"L'étape OTP est en {otp[0].get('requirement')} : elle ne sera jamais "
        "jouée.",
    )

    # LES CONDITIONS DU SOUS-FLUX DU SECOND FACTEUR, et non celles du flux
    # entier.
    #
    # Une copie du flux de navigateur contient DEUX sous-flux conditionnels,
    # « Conditional Organization » et « Conditional 2FA », chacun avec sa propre
    # `conditional-user-configured`. Celle du premier n'a rien à voir avec le
    # second facteur et doit rester : un test qui lirait le flux entier exigerait
    # de la retirer, ce qui casserait la connexion par organisation.
    sous_flux = [
        e.get("displayName") for e in executions
        if e.get("displayName") and "Conditional 2FA" in e["displayName"]
    ]
    assert sous_flux, message(
        en=f"The active flow \"{actif}\" has no second-factor subflow. "
        "Was it copied from the browser flow?",
        fr=f"Le flux actif « {actif} » n'a pas de sous-flux de second facteur. "
        "A-t-il été copié depuis le flux de navigateur ?",
    )
    du_sous_flux = _executions(idp, sous_flux[0])
    conditions = {
        e.get("providerId") for e in du_sous_flux
        if (e.get("providerId") or "").startswith("conditional-")
        and e.get("requirement") == "REQUIRED"
    }
    assert "conditional-user-role" in conditions, message(
        en="The second-factor subflow carries no active ROLE condition. Keycloak "
        "offers no group condition: targeting a team goes through "
        "a role, which the group carries. Active conditions: "
        f"{sorted(c for c in conditions if c)}",
        fr="Le sous-flux du second facteur ne porte aucune condition de RÔLE "
        "active. Keycloak "
        "n'offre pas de condition de groupe : le ciblage d'une équipe passe par "
        "un rôle, que le groupe porte. Conditions actives : "
        f"{sorted(c for c in conditions if c)}",
    )
    assert "conditional-user-configured" not in conditions, message(
        en="The second-factor subflow keeps `conditional-user-configured` "
        "active. That "
        "condition requires the second factor ONLY from those who already have one: "
        "an account that has none goes straight through, and you would believe you had "
        "imposed the second factor on a team that does not have it.",
        fr="Le sous-flux du second facteur garde `conditional-user-configured` "
        "active. Cette "
        "condition n'exige le second facteur QUE de ceux qui en ont déjà un : "
        "un compte qui n'en a aucun passe directement, et vous croiriez avoir "
        "imposé le second facteur à une équipe qui ne l'a pas.",
    )


def test_le_groupe_concerne_porte_vraiment_le_role(idp):
    """Le lien entre l'équipe et la condition, vérifié sur un compte réel.

    Vert avant le travail ? Non : le setup supprime tous les rôles du realm.

    Les rôles hérités d'un groupe n'apparaissent pas dans les rôles DIRECTS
    d'un compte : ils se lisent par `role-mappings/realm/composite`. Un test
    qui lirait les rôles directs conclurait que le groupe ne porte rien.
    """
    identifiants = _identifiants(idp)
    concerne = identifiants["COMPTE_CONCERNE"]
    epargne = identifiants["COMPTE_EPARGNE"]

    actif = _flux_actif(idp)
    executions = _executions(idp, actif)
    sous_flux = [
        e.get("displayName") for e in executions
        if e.get("displayName") and "Conditional 2FA" in e["displayName"]
    ]
    assert sous_flux, message(
        en=f"The active flow \"{actif}\" has no 2FA subflow.",
        fr=f"Le flux actif « {actif} » n'a pas de sous-flux 2FA.",
    )
    conditions = [
        e for e in _executions(idp, sous_flux[0])
        if e.get("providerId") == "conditional-user-role"
        and e.get("requirement") == "REQUIRED"
    ]
    assert conditions, message(
        en="No active role condition in the second-factor subflow.",
        fr="Aucune condition de rôle active dans le sous-flux du second facteur.",
    )

    configuration = _api(
        idp, f"realms/{REALM}/authentication/executions/"
        f"{conditions[0]['id']}/config/{conditions[0].get('authenticationConfig', '')}"
    ) if conditions[0].get("authenticationConfig") else None
    assert configuration and (configuration.get("config") or {}).get("condUserRole"), message(
        en="The role condition exists but is not configured: it names "
        "no role, and will therefore apply to nobody. A condition with no "
        "configuration is a condition that filters nothing.",
        fr="La condition de rôle existe mais n'est pas configurée : elle ne nomme "
        "aucun rôle, et ne s'appliquera donc à personne. Une condition sans "
        "configuration est une condition qui ne filtre rien.",
    )
    role_attendu = configuration["config"]["condUserRole"]

    for compte, doit_porter in ((concerne, True), (epargne, False)):
        trouves = _api(
            idp, f"realms/{REALM}/users?username={compte}&exact=true"
        ) or []
        assert trouves, message(
            en=f"The account \"{compte}\" cannot be found.",
            fr=f"Le compte « {compte} » est introuvable.",
        )
        effectifs = _api(
            idp,
            f"realms/{REALM}/users/{trouves[0]['id']}"
            "/role-mappings/realm/composite",
        ) or []
        noms = {r["name"] for r in effectifs}
        if doit_porter:
            assert role_attendu in noms, message(
                en=f"The account \"{compte}\", which is in the targeted group, does not "
                f"carry the role \"{role_attendu}\" that the condition names "
                f"(effective roles: {sorted(noms)}). The role must be attached "
                "TO THE GROUP, not to the account, otherwise every arrival in "
                "the team will need one more gesture.",
                fr=f"Le compte « {compte} », qui est dans le groupe concerné, ne "
                f"porte pas le rôle « {role_attendu} » que la condition nomme "
                f"(rôles effectifs : {sorted(noms)}). Le rôle doit être attaché "
                "AU GROUPE, pas au compte, sans quoi chaque arrivée dans "
                "l'équipe demandera un geste de plus.",
            )
        else:
            assert role_attendu not in noms, message(
                en=f"The account \"{compte}\", which must be spared, carries the role "
                f"\"{role_attendu}\". The second factor will be required of it too.",
                fr=f"Le compte « {compte} », qui doit être épargné, porte le rôle "
                f"« {role_attendu} ». Le second facteur lui sera exigé aussi.",
            )


def test_une_option_resistante_au_hameconnage_est_proposee(idp):
    """Un code à six chiffres se fait hameçonner, une clé non.

    Vert avant le travail ? Non : il n'y a pas de flux copié.

    Un code TOTP se recopie sur un faux site aussi facilement qu'un mot de
    passe. WebAuthn lie la preuve à l'origine du site : un faux site ne peut
    pas l'obtenir, même avec l'utilisateur devant lui.
    """
    actif = _flux_actif(idp)
    executions = _executions(idp, actif)

    proposees = {
        e.get("providerId") for e in executions
        if e.get("providerId") in RESISTANT_AU_HAMECONNAGE
        and e.get("requirement") in {"REQUIRED", "ALTERNATIVE"}
    }
    assert proposees, message(
        en="No phishing-resistant option is offered in the active "
        "flow. The WebAuthn steps are present there but disabled: "
        f"{[(e.get('providerId'), e.get('requirement')) for e in executions if e.get('providerId') in RESISTANT_AU_HAMECONNAGE]}",
        fr="Aucune option résistante au hameçonnage n'est proposée dans le flux "
        "actif. Les étapes WebAuthn y sont présentes mais désactivées : "
        f"{[(e.get('providerId'), e.get('requirement')) for e in executions if e.get('providerId') in RESISTANT_AU_HAMECONNAGE]}",
    )


def test_la_politique_de_mot_de_passe_suit_nist_800_63b_4(idp):
    """De la longueur, et aucune règle de composition ni d'expiration.

    Vert avant le travail ? Non : le setup retire toute politique du realm.

    NIST SP 800-63B-4 est explicite sur trois points, et ils vont à l'encontre
    de ce que la plupart des politiques imposent encore : une longueur
    minimale sérieuse, AUCUNE règle de composition, et AUCUNE expiration
    périodique. Les règles de composition produisent des mots de passe
    devinables (`Motdepasse1!`), et l'expiration périodique produit des
    variantes incrémentées.
    """
    politique = _le_realm(idp).get("passwordPolicy") or ""
    assert politique, message(
        en="The realm declares no password policy.",
        fr="Le realm ne déclare aucune politique de mot de passe.",
    )

    longueur = [
        morceau for morceau in politique.split(" and ")
        if morceau.strip().startswith("length(")
    ]
    assert longueur, message(
        en=f"The policy sets no minimum length: {politique!r}",
        fr=f"La politique ne fixe aucune longueur minimale : {politique!r}",
    )
    valeur = int(longueur[0].strip()[len("length("):-1])
    assert valeur >= 15, message(
        en=f"The minimum length is {valeur} characters. NIST SP 800-63B-4 "
        "settles on 15 when no other rule is imposed, and it is "
        "precisely because no other is that the length matters.",
        fr=f"La longueur minimale est de {valeur} caractères. NIST SP 800-63B-4 "
        "retient 15 quand aucune autre règle n'est imposée, et c'est "
        "précisément parce qu'aucune autre ne l'est que la longueur compte.",
    )

    fautives = [r for r in COMPOSITION_PROSCRITE if r in politique]
    assert not fautives, message(
        en=f"The policy imposes composition rules: {fautives}. "
        "NIST SP 800-63B-4 forbids them: they produce guessable "
        "passwords, because everybody satisfies the constraint the "
        f"same way. Policy read: {politique!r}",
        fr=f"La politique impose des règles de composition : {fautives}. "
        "NIST SP 800-63B-4 les proscrit : elles produisent des mots de passe "
        "devinables, parce que tout le monde satisfait la contrainte de la "
        f"même façon. Politique lue : {politique!r}",
    )
    assert "forceExpiredPasswordChange" not in politique, message(
        en="The policy imposes periodic expiry. NIST SP 800-63B-4 "
        "forbids it: it produces incremented variants of the same "
        f"password. Policy read: {politique!r}",
        fr="La politique impose une expiration périodique. NIST SP 800-63B-4 la "
        "proscrit : elle produit des variantes incrémentées du même mot de "
        f"passe. Politique lue : {politique!r}",
    )


def test_les_deux_connexions_se_terminent_differemment(idp):
    """LE TEST CENTRAL, et il joue les deux parcours.

    Vert avant le travail ? Non : le setup vérifie lui-même que les DEUX
    comptes se connectent dans la situation de départ.

    Les deux comptes ont le même mot de passe et aucun second facteur. Seule
    leur appartenance diffère. Le compte de l'équipe concernée doit être
    arrêté, l'autre doit passer.

    Mesuré le 2026-10-16 : un compte soumis au second facteur et qui n'en a
    aucun s'arrête sur « Mobile Authenticator Setup. You need to set up Mobile
    Authenticator to activate your account. »
    """
    identifiants = _identifiants(idp)

    epargne = _parcours(idp, identifiants["COMPTE_EPARGNE"])
    assert epargne.get("texte_trouve") is True, message(
        en=f"The account \"{identifiants['COMPTE_EPARGNE']}\", which must be "
        "spared, cannot log in. The second factor is therefore "
        "required of it too: that is the costliest failure case, because it affects "
        "the administrators as well and can lock everybody "
        f"out. Landed on: {epargne.get('arrivee')}, text: "
        f"{str(epargne.get('texte'))[:250]}",
        fr=f"Le compte « {identifiants['COMPTE_EPARGNE']} », qui doit être "
        "épargné, n'arrive pas à se connecter. Le second facteur lui est donc "
        "exigé aussi : c'est le cas d'échec le plus coûteux, parce qu'il touche "
        "aussi les administrateurs et qu'il peut enfermer tout le monde "
        f"dehors. Arrivée : {epargne.get('arrivee')}, texte : "
        f"{str(epargne.get('texte'))[:250]}",
    )

    concerne = _parcours(idp, identifiants["COMPTE_CONCERNE"])
    assert concerne.get("texte_trouve") is not True, message(
        en=f"The account \"{identifiants['COMPTE_CONCERNE'] }\", which is in "
        "the targeted team, logged in WITHOUT a second factor. The requirement "
        "is therefore not applied. If `conditional-user-configured` is still "
        "in your subflow, that is it: it requires the second factor only "
        "from those who already have one.",
        fr=f"Le compte « {identifiants['COMPTE_CONCERNE'] }», qui est dans "
        "l'équipe concernée, s'est connecté SANS second facteur. L'exigence "
        "n'est donc pas appliquée. Si `conditional-user-configured` est encore "
        "dans votre sous-flux, c'est elle : elle n'exige le second facteur que "
        "de ceux qui en ont déjà un.",
    )
    texte = str(concerne.get("texte") or "").lower()
    assert "authenticator" in texte or "authentification" in texte, message(
        en="The targeted account was indeed stopped, but not on a second-factor "
        f"enrolment screen. Landed on: {concerne.get('arrivee')}, "
        f"text: {str(concerne.get('texte'))[:250]}\n\n"
        "It must be invited to ENROL a second factor, not refused: "
        "an account required to provide what it cannot is an account "
        "locked out.",
        fr="Le compte concerné a bien été arrêté, mais pas sur un écran de "
        f"configuration de second facteur. Arrivée : {concerne.get('arrivee')}, "
        f"texte : {str(concerne.get('texte'))[:250]}\n\n"
        "Il doit être invité à ENREGISTRER un second facteur, et non refusé : "
        "un compte à qui on exige ce qu'il ne peut pas fournir est un compte "
        "enfermé dehors.",
    )
