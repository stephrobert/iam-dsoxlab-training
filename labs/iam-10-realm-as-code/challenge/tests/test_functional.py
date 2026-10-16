"""Un realm qui correspond à ses fichiers, une dérive qui se rattrape, et un
secret qui ne traîne nulle part.

CINQ FAITS MESURÉS LE 2026-10-16 QUI DÉCIDENT DE CES TESTS

1. Le provider `keycloak/keycloak` 5.10.0 parle à Keycloak 26.8.1, et il
   s'installe au `terraform init` en s'annonçant « self-signed » avec
   l'empreinte de sa clef. Ce n'est pas une alerte : c'est la signature d'un
   éditeur qui n'est pas HashiCorp.

2. `terraform plan -detailed-exitcode` rend **0** quand l'état correspond aux
   fichiers et **2** quand il en diffère. C'est ce code, et non la lecture de
   la sortie, qui permet de juger la correspondance.

3. Une dérive introduite par l'API d'administration est bien vue par le plan,
   qui l'affiche en comparant les deux représentations
   (`"30m0s" -> "10m"` pour une durée), et `apply` la corrige.

4. LE PIÈGE : le secret d'un client confidentiel se retrouve **en clair dans
   `terraform.tfstate`**, créé en **644**, alors même que les fichiers `.tf`
   ne portent que le nom d'une variable, et que `sensitive = true` masque les
   sorties de `plan` et d'`apply`. « Je n'ai pas écrit le secret dans mon
   code » n'est donc pas « mon secret n'est nulle part en clair ».

5. Le provider lit ses justificatifs dans `KEYCLOAK_URL`, `KEYCLOAK_USER`,
   `KEYCLOAK_PASSWORD` et `KEYCLOAK_REALM`. Aucun mot de passe n'a besoin
   d'être écrit dans un fichier.
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
SECRETS_DU_SOCLE = "/opt/socle-iam/.env"

#: Les extensions des fichiers que l'apprenant écrit, et dans lesquels aucun
#: justificatif ne doit se trouver.
FICHIERS_ECRITS = ("*.tf", "*.tfvars", "*.tfvars.json", "*.auto.tfvars")

#: Le mode le plus permissif acceptable pour un fichier qui porte un secret.
#: 0640 passe (propriétaire et groupe), 0644 ne passe pas.
MODE_MAXIMAL_ETAT = 0o640


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


def _jeton_admin(hote, ids: dict[str, str]) -> str:
    env = hote.file(SECRETS_DU_SOCLE).content_string
    compte = {}
    for ligne in env.splitlines():
        if ligne.startswith("KC_BOOTSTRAP_ADMIN_"):
            clef, _, valeur = ligne.partition("=")
            compte[clef] = valeur
    res = hote.run(
        f"curl -sS --max-time 20 -X POST "
        f"{ids['KEYCLOAK_URL']}/realms/master/protocol/openid-connect/token "
        f"-d grant_type=password -d client_id=admin-cli "
        f"-d username={shlex.quote(compte['KC_BOOTSTRAP_ADMIN_USERNAME'])} "
        f"-d password={shlex.quote(compte['KC_BOOTSTRAP_ADMIN_PASSWORD'])}")
    try:
        return json.loads(res.stdout)["access_token"]
    except (json.JSONDecodeError, KeyError):
        pytest.fail(message(
            en=f"No administration token: {res.stdout[:200]!r}",
            fr=f"Pas de jeton d'administration : {res.stdout[:200]!r}",
        ))


def _api(hote, ids: dict[str, str], jeton: str, chemin: str, *,
         brut: bool = False):
    res = hote.run(
        f"curl -sS --max-time 30 {ids['KEYCLOAK_URL']}/admin/{chemin} "
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


def _realm_decrit(hote, ids: dict[str, str], jeton: str) -> dict:
    """Le realm que l'apprenant doit décrire, ou un échec qui le dit.

    Keycloak répond `{"error":"Realm not found."}` pour un realm absent : c'est
    du JSON, et il commence par une accolade. Un test qui se contenterait de
    vérifier la forme le prendrait pour un realm, puis planterait en
    interrogeant ses sous-ressources, sur une AttributeError qui n'apprend
    rien à personne.
    """
    brut = _api(hote, ids, jeton, f"realms/{ids['REALM_A_DECRIRE']}", brut=True)
    try:
        charge = json.loads(brut)
    except json.JSONDecodeError:
        pytest.fail(message(
            en=f"Unreadable answer for the realm "
                    f"\"{ids['REALM_A_DECRIRE']}\": {brut[:200]!r}",
            fr=f"Réponse illisible pour le realm "
                    f"« {ids['REALM_A_DECRIRE']} » : {brut[:200]!r}",
        ))
    assert isinstance(charge, dict) and charge.get("realm") == ids[
        "REALM_A_DECRIRE"], message(
        en=f"The realm \"{ids['REALM_A_DECRIRE']}\" does not exist. The provider "
        f"answers: {brut[:200]!r}",
        fr=f"Le realm « {ids['REALM_A_DECRIRE']} » n'existe pas. Le fournisseur "
        f"répond : {brut[:200]!r}",
    )
    return charge


def _secret_du_client(hote, ids: dict[str, str], jeton: str) -> str:
    """Le secret ACTUEL du client confidentiel, lu par l'API.

    Il sert à deux choses : vérifier qu'il n'est pas écrit en clair dans le
    code, et le rendre à Terraform quand les tests rejouent le code de
    l'apprenant. Sans lui, `plan` sortirait en erreur sur une variable sans
    valeur, et le test accuserait le code de ne pas décrire le realm.
    """
    clients = _api(hote, ids, jeton,
                   f"realms/{ids['REALM_A_DECRIRE']}/clients")
    if not isinstance(clients, list):
        # Realm absent : l'API rend un objet d'erreur, pas une liste.
        return ""
    for client in clients:
        if client.get("clientId") == ids["CLIENT_CONFIDENTIEL_ATTENDU"]:
            secret = _api(
                hote, ids, jeton,
                f"realms/{ids['REALM_A_DECRIRE']}/clients/{client['id']}"
                "/client-secret")
            if isinstance(secret, dict):
                return secret.get("value", "")
    return ""


def _terraform(hote, ids: dict[str, str], arguments: str, *,
               secret: str = "") -> object:
    """`terraform` dans le répertoire de travail, avec l'environnement voulu.

    Les justificatifs viennent du fichier du socle, et non d'un fichier de
    l'apprenant : un test qui aurait besoin que l'apprenant les ait écrits
    quelque part noterait le contraire de ce que le lab enseigne.

    `secret` est passé sous le nom que le cahier des charges impose
    (`VARIABLE_SECRET_ATTENDUE`), parce que rejouer le code de quelqu'un exige
    de pouvoir lui fournir ses entrées.
    """
    env = hote.file(SECRETS_DU_SOCLE).content_string
    compte = {}
    for ligne in env.splitlines():
        if ligne.startswith("KC_BOOTSTRAP_ADMIN_"):
            clef, _, valeur = ligne.partition("=")
            compte[clef] = valeur
    prefixe = (
        f"cd {shlex.quote(ids['REPERTOIRE_TRAVAIL'])} && "
        f"KEYCLOAK_URL={shlex.quote(ids['KEYCLOAK_URL'])} "
        f"KEYCLOAK_USER={shlex.quote(compte['KC_BOOTSTRAP_ADMIN_USERNAME'])} "
        f"KEYCLOAK_PASSWORD={shlex.quote(compte['KC_BOOTSTRAP_ADMIN_PASSWORD'])} "
        "KEYCLOAK_REALM=master "
        "KEYCLOAK_CLIENT_ID=admin-cli "
    )
    if secret:
        nom = ids["VARIABLE_SECRET_ATTENDUE"]
        prefixe += f"TF_VAR_{nom}={shlex.quote(secret)} "
    return hote.run(f"{prefixe} terraform {arguments}")


# ── 1. Le realm décrit existe, tel que décrit ───────────────────────────────


def test_des_fichiers_decrivent_le_realm(idp):
    """Il y a du code, et un état : le realm n'a pas été fait à la main.

    Un realm créé à la console passerait les contrôles de contenu qui suivent.
    Ce test est celui qui distingue « le résultat est là » de « le résultat est
    décrit quelque part ».
    """
    ids = _identifiants(idp)
    travail = ids["REPERTOIRE_TRAVAIL"]

    fichiers = idp.run(f"find {travail} -maxdepth 1 -name '*.tf' | sort")
    assert fichiers.stdout.strip(), message(
        en=f"No `.tf` file in {travail}. The realm must be DESCRIBED, not "
        "merely created.",
        fr=f"Aucun fichier `.tf` dans {travail}. Le realm doit être DÉCRIT, pas "
        "seulement créé.",
    )

    etat = idp.file(f"{travail}/terraform.tfstate")
    assert etat.exists, message(
        en=f"{travail}/terraform.tfstate is missing: the files were never "
        "applied, or the state is elsewhere. With no state, nothing links the "
        "code to the realm, and the next application would recreate everything.",
        fr=f"{travail}/terraform.tfstate est absent : les fichiers n'ont jamais "
        "été appliqués, ou l'état est ailleurs. Sans état, rien ne relie le "
        "code au realm, et la prochaine application recréerait tout.",
    )

    contenu = " ".join(
        idp.file(c).content_string
        for c in fichiers.stdout.split() if c.strip())
    assert ids["VERSION_PROVIDER"] in contenu, message(
        en=f"The provider's version ({ids['VERSION_PROVIDER']}) is not pinned "
        "in the files. With no version constraint, an application in six "
        "months would use another provider.",
        fr=f"La version du provider ({ids['VERSION_PROVIDER']}) n'est pas "
        "épinglée dans les fichiers. Sans contrainte de version, une "
        "application dans six mois utiliserait un autre provider.",
    )


def test_le_realm_porte_ce_qui_est_decrit(idp):
    """Le realm, ses réglages, ses rôles, son groupe et ses deux clients."""
    ids = _identifiants(idp)
    jeton = _jeton_admin(idp, ids)
    realm = ids["REALM_A_DECRIRE"]

    decrit = _realm_decrit(idp, ids, jeton)

    assert decrit.get("enabled") is True, message(
        en=f"The realm \"{realm}\" is disabled.",
        fr=f"Le realm « {realm} » est désactivé.",
    )
    assert decrit.get("displayName") == ids["DISPLAY_NAME_ATTENDU"], message(
        en=f"displayName is {decrit.get('displayName')!r} instead of "
        f"{ids['DISPLAY_NAME_ATTENDU']!r}.",
        fr=f"displayName vaut {decrit.get('displayName')!r} au lieu de "
        f"{ids['DISPLAY_NAME_ATTENDU']!r}.",
    )
    assert str(decrit.get("accessTokenLifespan")) == ids["DUREE_JETON_ATTENDUE"], message(
        en=f"accessTokenLifespan is {decrit.get('accessTokenLifespan')!r} instead "
        f"of {ids['DUREE_JETON_ATTENDUE']}. The provider accepts \"10m\" as "
        "readily as seconds, and the API returns seconds.",
        fr=f"accessTokenLifespan vaut {decrit.get('accessTokenLifespan')!r} au "
        f"lieu de {ids['DUREE_JETON_ATTENDUE']}. Le provider accepte « 10m » "
        "aussi bien que des secondes, et l'API rend des secondes.",
    )

    roles = {r["name"] for r in _api(idp, ids, jeton, f"realms/{realm}/roles")}
    attendus = set(ids["ROLES_ATTENDUS"].split())
    assert attendus <= roles, message(
        en=f"Missing roles: {sorted(attendus - roles)}. Present: "
        f"{sorted(r for r in roles if not r.startswith('default-roles'))}",
        fr=f"Rôles manquants : {sorted(attendus - roles)}. Présents : "
        f"{sorted(r for r in roles if not r.startswith('default-roles'))}",
    )

    groupes = {g["name"] for g in _api(idp, ids, jeton, f"realms/{realm}/groups")}
    assert ids["GROUPE_ATTENDU"] in groupes, message(
        en=f"The group \"{ids['GROUPE_ATTENDU']}\" is missing: {sorted(groupes)}",
        fr=f"Le groupe « {ids['GROUPE_ATTENDU']} » est absent : {sorted(groupes)}",
    )

    clients = _api(idp, ids, jeton, f"realms/{realm}/clients")
    par_id = {c["clientId"]: c for c in clients}

    public = par_id.get(ids["CLIENT_PUBLIC_ATTENDU"])
    assert public is not None, message(
        en=f"The client \"{ids['CLIENT_PUBLIC_ATTENDU']}\" is missing: "
        f"{sorted(par_id)}",
        fr=f"Le client « {ids['CLIENT_PUBLIC_ATTENDU']} » est absent : "
        f"{sorted(par_id)}",
    )
    assert public.get("publicClient") is True, message(
        en=f"\"{ids['CLIENT_PUBLIC_ATTENDU']}\" is not public.",
        fr=f"« {ids['CLIENT_PUBLIC_ATTENDU']} » n'est pas public.",
    )
    assert public.get("attributes", {}).get(
        "pkce.code.challenge.method") == "S256", message(
        en=f"\"{ids['CLIENT_PUBLIC_ATTENDU']}\" does not require PKCE S256. A "
        "public client with no PKCE leaves an authorization code usable by "
        "whoever intercepts it.",
        fr=f"« {ids['CLIENT_PUBLIC_ATTENDU']} » n'exige pas PKCE S256. Un client "
        "public sans PKCE laisse un code d'autorisation utilisable par qui "
        "l'intercepte.",
    )

    confidentiel = par_id.get(ids["CLIENT_CONFIDENTIEL_ATTENDU"])
    assert confidentiel is not None, message(
        en=f"The client \"{ids['CLIENT_CONFIDENTIEL_ATTENDU']}\" is missing: "
        f"{sorted(par_id)}",
        fr=f"Le client « {ids['CLIENT_CONFIDENTIEL_ATTENDU']} » est absent : "
        f"{sorted(par_id)}",
    )
    assert confidentiel.get("publicClient") is False, message(
        en=f"\"{ids['CLIENT_CONFIDENTIEL_ATTENDU']}\" should be confidential.",
        fr=f"« {ids['CLIENT_CONFIDENTIEL_ATTENDU']} » devrait être confidentiel.",
    )


# ── 2. Le code et le realm disent la même chose ─────────────────────────────


def test_l_etat_correspond_aux_fichiers(idp):
    """`plan -detailed-exitcode` rend 0, ou le code ne décrit pas le realm.

    C'est le code de sortie qui juge, et non la lecture de la sortie : un plan
    qui annonce des changements veut dire que ce qui tourne n'est pas ce qui
    est écrit.
    """
    ids = _identifiants(idp)
    jeton = _jeton_admin(idp, ids)
    plan = _terraform(idp, ids, "plan -detailed-exitcode -no-color -input=false",
                      secret=_secret_du_client(idp, ids, jeton))
    assert plan.rc != 1, message(
        en="Terraform could not establish a plan:\n"
        f"{plan.stdout[-800:]}{plan.stderr[-500:]}",
        fr="Terraform n'a pas pu établir de plan :\n"
        f"{plan.stdout[-800:]}{plan.stderr[-500:]}",
    )
    assert plan.rc == 0, message(
        en="The plan announces changes: the realm that runs is not the one the "
        "files describe.\n"
        f"{plan.stdout[-900:]}",
        fr="Le plan annonce des changements : le realm qui tourne n'est pas "
        "celui que décrivent les fichiers.\n"
        f"{plan.stdout[-900:]}",
    )


def test_une_derive_faite_a_la_main_est_rattrapee(idp):
    """Le test introduit une dérive, et exige que la réapplication la corrige.

    C'est le seul contrôle qui prouve ce que le lab enseigne. Il modifie donc
    l'état, puis le fait rétablir par les fichiers de l'apprenant, ce qui est
    exactement le geste à éprouver. Si la réapplication échoue, la dérive est
    rétablie à la main pour ne pas laisser le realm dans un état faux.
    """
    ids = _identifiants(idp)
    jeton = _jeton_admin(idp, ids)
    realm = ids["REALM_A_DECRIRE"]
    attendue = int(ids["DUREE_JETON_ATTENDUE"])
    deviee = attendue + 1200

    avant = _realm_decrit(idp, ids, jeton)
    assert int(avant["accessTokenLifespan"]) == attendue, message(
        en="The starting setting is not the one described: this test can "
        f"measure nothing. accessTokenLifespan = {avant['accessTokenLifespan']}",
        fr="Le réglage de départ n'est pas celui décrit : ce test ne peut rien "
        f"mesurer. accessTokenLifespan = {avant['accessTokenLifespan']}",
    )

    def _poser(valeur: int) -> str:
        lu = _api(idp, ids, jeton, f"realms/{realm}", brut=True)
        idp.run(
            f"printf %s {shlex.quote(lu)} "
            f"| jq '.accessTokenLifespan = {valeur}' > /tmp/derive-iam10.json")
        pose = idp.run(
            f"curl -sS --max-time 20 -o /dev/null -w '%{{http_code}}' -X PUT "
            f"{ids['KEYCLOAK_URL']}/admin/realms/{realm} "
            f"-H {shlex.quote('Authorization: Bearer ' + jeton)} "
            "-H 'Content-Type: application/json' -d @/tmp/derive-iam10.json")
        return pose.stdout.strip()

    code = _poser(deviee)
    assert code == "204", message(
        en=f"The drift could not be introduced: HTTP {code}",
        fr=f"La dérive n'a pas pu être posée : HTTP {code}",
    )

    try:
        apres_derive = json.loads(
            _api(idp, ids, jeton, f"realms/{realm}", brut=True))
        assert int(apres_derive["accessTokenLifespan"]) == deviee, message(
            en="The drift did not take: the test measures nothing.",
            fr="La dérive n'a pas pris : le test ne mesure rien.",
        )

        secret = _secret_du_client(idp, ids, jeton)
        plan = _terraform(
            idp, ids, "plan -detailed-exitcode -no-color -input=false",
            secret=secret)
        assert plan.rc == 2, message(
            en=f"The plan did not see the drift (code {plan.rc}, 2 expected). Is the "
            "modified setting really described in the files? A setting absent "
            "from the code is not a drift for Terraform: it is a value it does "
            "not deal with.\n"
            f"{plan.stdout[-700:]}",
            fr=f"Le plan n'a pas vu la dérive (code {plan.rc}, 2 attendu). Le "
            "réglage modifié est-il bien décrit dans les fichiers ? Un réglage "
            "absent du code n'est pas une dérive pour Terraform : c'est une "
            "valeur dont il ne s'occupe pas.\n"
            f"{plan.stdout[-700:]}",
        )

        applique = _terraform(
            idp, ids, "apply -auto-approve -no-color -input=false",
            secret=secret)
        assert applique.rc == 0, message(
            en="Reapplying failed, and the drift remains:\n"
            f"{applique.stdout[-800:]}{applique.stderr[-500:]}",
            fr="La réapplication a échoué, et la dérive reste :\n"
            f"{applique.stdout[-800:]}{applique.stderr[-500:]}",
        )

        final = json.loads(_api(idp, ids, jeton, f"realms/{realm}", brut=True))
        assert int(final["accessTokenLifespan"]) == attendue, message(
            en=f"After reapplying, accessTokenLifespan is "
            f"{final['accessTokenLifespan']} and not {attendue}: the files did "
            "not take this setting back in hand.",
            fr=f"Après réapplication, accessTokenLifespan vaut "
            f"{final['accessTokenLifespan']} et non {attendue} : les fichiers "
            "n'ont pas repris la main sur ce réglage.",
        )
    finally:
        # Si quelque chose a échoué au milieu, le realm ne reste pas dévié : un
        # test qui laisse l'état faux fait échouer les suivants pour une raison
        # qui n'est pas la leur.
        courant = json.loads(
            _api(idp, ids, jeton, f"realms/{realm}", brut=True))
        if int(courant["accessTokenLifespan"]) != attendue:
            _poser(attendue)
        idp.run("rm -f /tmp/derive-iam10.json")


# ── 3. Ce qui ne doit traîner nulle part ────────────────────────────────────


def test_aucun_justificatif_dans_les_fichiers_ecrits(idp):
    """Ni le mot de passe du socle, ni le secret du client, dans le code.

    Le secret est relu par l'API : un apprenant qui l'aurait écrit en dur dans
    son code serait attrapé même s'il l'a tiré lui-même.
    """
    ids = _identifiants(idp)
    jeton = _jeton_admin(idp, ids)
    travail = ids["REPERTOIRE_TRAVAIL"]

    motifs = []
    env = idp.file(SECRETS_DU_SOCLE).content_string
    for ligne in env.splitlines():
        if ligne.startswith("KC_BOOTSTRAP_ADMIN_PASSWORD="):
            motifs.append(("le mot de passe d'administration du socle",
                           ligne.partition("=")[2]))

    _realm_decrit(idp, ids, jeton)
    clients = _api(idp, ids, jeton,
                   f"realms/{ids['REALM_A_DECRIRE']}/clients")
    for client in clients:
        if client.get("clientId") == ids["CLIENT_CONFIDENTIEL_ATTENDU"]:
            secret = _api(
                idp, ids, jeton,
                f"realms/{ids['REALM_A_DECRIRE']}/clients/{client['id']}"
                "/client-secret")
            if isinstance(secret, dict) and secret.get("value"):
                motifs.append(("le secret du client confidentiel",
                               secret["value"]))

    assert motifs, message(
        en="This test found no credential to look for: it therefore measures "
        "nothing. Does the confidential client exist, and does the base have "
        "its environment file?",
        fr="Ce test n'a trouvé aucun justificatif à chercher : il ne mesure donc "
        "rien. Le client confidentiel existe-t-il, et le socle a-t-il son "
        "fichier d'environnement ?",
    )

    for quoi, valeur in motifs:
        for motif_fichier in FICHIERS_ECRITS:
            trouve = idp.run(
                f"find {travail} -maxdepth 1 -name {shlex.quote(motif_fichier)} "
                f"-exec grep -l -F {shlex.quote(valeur)} {{}} +")
            assert not trouve.stdout.strip(), message(
                en=f"{quoi} is written in clear in "
                f"{trouve.stdout.strip()}. The provider reads its credentials "
                "from the environment (KEYCLOAK_USER, KEYCLOAK_PASSWORD), and "
                "a client secret is passed through a variable, not as a "
                "literal value.",
                fr=f"{quoi} est écrit en clair dans "
                f"{trouve.stdout.strip()}. Le provider lit ses justificatifs "
                "dans l'environnement (KEYCLOAK_USER, KEYCLOAK_PASSWORD), et "
                "un secret de client se passe par une variable, pas par une "
                "valeur littérale.",
            )


def test_le_fichier_d_etat_est_protege(idp):
    """LE PIÈGE : le secret du client confidentiel est en clair dans l'état.

    Mesuré le 2026-10-16 : les fichiers `.tf` ne portent que le nom d'une
    variable, `sensitive = true` masque les sorties, et `terraform.tfstate`
    contient quand même le secret, en clair, créé en 644.

    Ne pas écrire un secret dans son code n'est donc pas la même chose que ne
    pas l'avoir en clair sur le disque.
    """
    ids = _identifiants(idp)
    etat = idp.file(f"{ids['REPERTOIRE_TRAVAIL']}/terraform.tfstate")
    assert etat.exists, message(
        en="No state file: nothing was applied.",
        fr="Pas de fichier d'état : rien n'a été appliqué.",
    )

    assert etat.mode <= MODE_MAXIMAL_ETAT, message(
        en=f"{ids['REPERTOIRE_TRAVAIL']}/terraform.tfstate is in "
        f"{oct(etat.mode)}, readable beyond its group. That file contains "
        "the confidential client's secret IN CLEAR, whatever your `.tf` files "
        f"may say. At most {oct(MODE_MAXIMAL_ETAT)} was expected.",
        fr=f"{ids['REPERTOIRE_TRAVAIL']}/terraform.tfstate est en "
        f"{oct(etat.mode)}, lisible au-delà de son groupe. Ce fichier contient "
        "le secret du client confidentiel EN CLAIR, quoi que disent vos "
        f"fichiers `.tf`. Attendu au plus {oct(MODE_MAXIMAL_ETAT)}.",
    )

    # ET LE RÉPERTOIRE, parce qu'un fichier ne suffit pas.
    #
    # Mesuré le 2026-10-16 : Terraform préserve les droits du
    # `terraform.tfstate` qui existe déjà, puisqu'il écrit dedans, mais il
    # RECRÉE `terraform.tfstate.backup` en 644 à chaque application. Protéger
    # ce fichier une fois ne tient donc pas une application de plus.
    #
    # Ce qui tient, c'est le répertoire : quoi que l'outil y recrée, personne
    # d'autre n'y entre.
    travail = idp.file(ids["REPERTOIRE_TRAVAIL"])
    assert travail.mode & 0o007 == 0, message(
        en=f"{ids['REPERTOIRE_TRAVAIL']} is in {oct(travail.mode)}: everybody "
        "can enter it. The state file carries the confidential client's "
        "secret there, and its BACKUP is recreated in 644 on every "
        "application, whatever rights you had given it. "
        "Only the directory durably protects what the tool recreates.",
        fr=f"{ids['REPERTOIRE_TRAVAIL']} est en {oct(travail.mode)} : tout le "
        "monde peut y entrer. Le fichier d'état y porte le secret du client "
        "confidentiel, et sa SAUVEGARDE est recréée en 644 à chaque "
        "application, quels que soient les droits que vous lui aviez donnés. "
        "Seul le répertoire protège durablement ce que l'outil recrée.",
    )


def test_le_realm_du_socle_n_a_pas_ete_touche(idp):
    """Le cas d'échec : appliquer sur le mauvais realm.

    Le provider pointe sur un realm par son `realm_id`, et son environnement
    nomme celui où il s'authentifie. Une confusion entre les deux applique le
    cahier des charges sur le realm d'administration, ou sur celui que les
    autres labs utilisent.
    """
    ids = _identifiants(idp)
    jeton = _jeton_admin(idp, ids)

    # Constater que le socle est intact ne mesure rien tant que rien n'a été
    # appliqué : sans ce préalable, ce test serait vert sur un lab pas
    # commencé.
    _realm_decrit(idp, ids, jeton)

    intrus = {ids["CLIENT_PUBLIC_ATTENDU"], ids["CLIENT_CONFIDENTIEL_ATTENDU"]}

    for realm in ("master", "formation"):
        brut = _api(idp, ids, jeton, f"realms/{realm}/clients", brut=True)
        if not brut.strip().startswith("["):
            continue
        presents = {c.get("clientId") for c in json.loads(brut)}
        fautifs = intrus & presents
        assert not fautifs, message(
            en=f"The clients {sorted(fautifs)} were created in the realm "
            f"\"{realm}\", which is not the one in the specification. The "
            "resources' `realm_id` must designate the realm being described, "
            "not the one where the provider authenticates.",
            fr=f"Les clients {sorted(fautifs)} ont été créés dans le realm "
            f"« {realm} », qui n'est pas celui du cahier des charges. Le "
            "`realm_id` des ressources doit désigner le realm décrit, et non "
            "celui où le provider s'authentifie.",
        )

    # Le realm du socle doit aussi avoir gardé SES propres réglages : un
    # cahier des charges appliqué dessus écraserait sa durée de jeton sans
    # créer aucun client, donc sans que le contrôle ci-dessus le voie.
    formation = _api(idp, ids, jeton, "realms/formation", brut=True)
    assert formation.strip().startswith("{"), message(
        en="The base's \"formation\" realm no longer answers: "
        f"{formation[:200]!r}",
        fr="Le realm « formation » du socle ne répond plus : "
        f"{formation[:200]!r}",
    )
    assert json.loads(formation).get("displayName") != ids[
        "DISPLAY_NAME_ATTENDU"], message(
        en="The base's \"formation\" realm carries the specification's "
        "displayName: the files were applied to it. The thirteen other labs "
        "use it.",
        fr="Le realm « formation » du socle porte le displayName du cahier des "
        "charges : les fichiers ont été appliqués sur lui. Les treize autres "
        "labs s'en servent.",
    )
