"""L'import qui a vraiment eu lieu, et l'écriture que le fournisseur refuse.

Aucun test ne lit la configuration de la fédération pour la juger bonne. Ils
regardent ce que le fournisseur CONNAÎT après la synchronisation, et ce qu'il
REFUSE de faire.

LE PIÈGE MESURÉ, ET POURQUOI IL EST SILENCIEUX

Keycloak tourne dans un conteneur. Mesuré le 2026-10-16 depuis ce conteneur :

    127.0.0.1:3890    fermé
    lldap:3890        ouvert

Avec `ldap://127.0.0.1:3890`, la synchronisation rend
« 0 imported users, 0 updated users » et HTTP 200. Aucune erreur, aucun
avertissement : la fédération est déclarée, elle est active, et elle ne voit
personne. C'est le défaut que ces tests existent pour attraper.

CE QUI ARRIVE EN PLUS, ET QUI N'EST PAS UNE FAUTE

L'annuaire porte son propre compte d'administration et trois groupes
`lldap_*`. Ils sont importés avec le reste, et les tests ne les comptent pas
comme des erreurs : ils vérifient que les bonnes personnes et les bons groupes
sont là, avec les bons membres, pas que rien d'autre n'a suivi.
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
IDENTIFIANTS = "/opt/iam-lab/identifiants-lab.txt"
SECRETS_DU_SOCLE = "/opt/socle-iam/.env"

#: Les personnes de l'annuaire, et leur adresse.
PERSONNES = {
    "aline": "aline@formation.lab",
    "bruno": "bruno@formation.lab",
    "chloe": "chloe@formation.lab",
}

#: Les groupes attendus, et leurs membres exacts.
GROUPES = {
    "devops": {"aline", "bruno"},
    "lecteurs": {"bruno", "chloe"},
}


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
    """Un jeton d'administration, obtenu avec le compte du socle.

    Sans `set -o pipefail` : testinfra exécute par `/bin/sh`, qui est `dash`
    sur Ubuntu et répond « set: Illegal option -o pipefail ». Le résultat est
    vérifié juste après, ce qui vaut mieux qu'un code de retour de tube.
    """
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


def _api(hote, chemin: str, methode: str = "GET", corps: str | None = None) -> object:
    jeton = _jeton_admin(hote)
    donnees = f" -H 'Content-Type: application/json' -d {corps!r}" if corps else ""
    res = hote.run(
        f"curl -sS --max-time 60 -X {methode} "
        f"'{KEYCLOAK}/admin/realms/{REALM}/{chemin}' "
        f"-H 'Authorization: Bearer {jeton}'{donnees}"
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


def _federation(hote) -> dict:
    """Le composant de fédération déclaré dans le realm."""
    realm = _api(hote, "")
    assert isinstance(realm, dict) and realm.get("id"), message(
        en=f"The realm \"{REALM}\" cannot be found.",
        fr=f"Le realm « {REALM} » est introuvable.",
    )
    composants = _api(
        hote,
        f"components?parent={realm['id']}"
        "&type=org.keycloak.storage.UserStorageProvider",
    ) or []
    ldap = [c for c in composants if c.get("providerId") == "ldap"]
    assert ldap, message(
        en=f"No LDAP federation declared in the realm \"{REALM}\". That is the "
        "challenge's first move: the provider must know where to read the "
        "accounts.",
        fr=f"Aucune fédération LDAP déclarée dans le realm « {REALM} ». C'est le "
        "premier geste du challenge : le fournisseur doit savoir où lire les "
        "comptes.",
    )
    assert len(ldap) == 1, message(
        en=f"{len(ldap)} LDAP federations are declared. A single one is expected, "
        "otherwise the priority order decides who answers and the result becomes "
        "unpredictable.",
        fr=f"{len(ldap)} fédérations LDAP sont déclarées. Une seule est attendue, "
        "sinon l'ordre de priorité décide de qui répond et le résultat devient "
        "imprévisible.",
    )
    return ldap[0]


def _config(composant: dict, clef: str) -> str:
    """Une valeur de configuration, qui arrive toujours en LISTE.

    L'API d'administration rend chaque valeur de `config` dans une liste, même
    quand elle est unique. Lire la valeur directement donnerait une liste et
    toutes les comparaisons échoueraient.
    """
    valeurs = (composant.get("config") or {}).get(clef) or []
    return valeurs[0] if valeurs else ""


def _comptes_du_realm(hote) -> dict[str, dict]:
    comptes = _api(hote, "users?briefRepresentation=true&max=200") or []
    return {c["username"]: c for c in comptes}


def _groupes_du_realm(hote) -> dict[str, str]:
    groupes = _api(hote, "groups?max=200") or []
    return {g["name"]: g["id"] for g in groupes}


# ── Les tests ────────────────────────────────────────────────────────────────


def test_la_federation_est_declaree_en_lecture_seule(idp):
    """Le mode d'édition, puis le refus réel. Le premier sans le second ne vaut
    rien.

    Vert avant le travail ? Non : le setup retire toute fédération.

    Une fédération en écriture laisse le fournisseur modifier l'annuaire, qui
    est la source. Le jour où quelqu'un corrige un nom dans la console, c'est
    l'annuaire qui change, et plus personne ne sait d'où vient la donnée.
    """
    federation = _federation(idp)

    mode = _config(federation, "editMode")
    assert mode == "READ_ONLY", message(
        en=f"The federation is in \"{mode or 'undeclared'}\" mode instead of "
        "READ_ONLY. The provider could write into the directory, which is the "
        "source of truth.",
        fr=f"La fédération est en mode « {mode or 'non déclaré'} » au lieu de "
        "READ_ONLY. Le fournisseur pourrait écrire dans l'annuaire, qui est la "
        "source de vérité.",
    )
    assert _config(federation, "enabled") == "true", message(
        en="The federation is declared but disabled: it will read nothing.",
        fr="La fédération est déclarée mais désactivée : elle ne lira rien.",
    )
    assert _config(federation, "importEnabled") == "true", message(
        en="Import is disabled. The accounts will not be known to the realm, and "
        "the groups cannot be attached to them.",
        fr="L'import est désactivé. Les comptes ne seront pas connus du realm, et "
        "les groupes ne pourront pas leur être attachés.",
    )


def test_la_synchronisation_a_vraiment_importe_les_comptes(idp):
    """LE TEST CENTRAL : les trois personnes sont connues du fournisseur.

    Vert avant le travail ? Non : le realm ne connaît aucun compte au départ,
    et le nettoyage le vérifie.

    C'est ici que se voit le piège de l'adresse de connexion. Avec
    `ldap://127.0.0.1:3890`, la fédération se déclare, s'active, et importe
    zéro compte en répondant HTTP 200. Mesuré le 2026-10-16 : depuis le
    conteneur de Keycloak, `127.0.0.1:3890` est fermé et `lldap:3890` est
    ouvert.
    """
    comptes = _comptes_du_realm(idp)

    manquants = sorted(set(PERSONNES) - set(comptes))
    assert not manquants, message(
        en=f"The realm does not know {manquants}.\n\n"
        "If the synchronisation answered \"0 imported users\" without an error, "
        "the connection address is at fault: Keycloak runs inside a "
        "container, and its `127.0.0.1` is not the machine. Measured from that "
        "container, `127.0.0.1:3890` is closed and `lldap:3890` is open.\n"
        f"Accounts known to the realm: {sorted(comptes)}",
        fr=f"Le realm ne connaît pas {manquants}.\n\n"
        "Si la synchronisation a répondu « 0 imported users » sans erreur, "
        "l'adresse de connexion est en cause : Keycloak tourne dans un "
        "conteneur, et son `127.0.0.1` n'est pas la machine. Mesuré depuis ce "
        "conteneur, `127.0.0.1:3890` est fermé et `lldap:3890` est ouvert.\n"
        f"Comptes connus du realm : {sorted(comptes)}",
    )

    for nom, adresse in PERSONNES.items():
        compte = comptes[nom]
        assert compte.get("federationLink"), message(
            en=f"The account \"{nom}\" exists in the realm but is not attached "
            "to the federation. It was created by hand, and it will not follow "
            "the directory.",
            fr=f"Le compte « {nom} » existe dans le realm mais n'est pas rattaché "
            "à la fédération. Il a été créé à la main, et il ne suivra pas "
            "l'annuaire.",
        )
        assert compte.get("email") == adresse, message(
            en=f"The account \"{nom}\" carries the address {compte.get('email')!r} instead "
            f"of {adresse!r}. Is the mail attribute being projected?",
            fr=f"Le compte « {nom} » porte l'adresse {compte.get('email')!r} au "
            f"lieu de {adresse!r}. L'attribut de courriel est-il projeté ?",
        )


def test_le_mappeur_de_groupes_existe_et_vise_la_bonne_branche(idp):
    """Sans mappeur, les comptes arrivent sans aucun groupe.

    Vert avant le travail ? Non : il n'y a pas de fédération, donc pas de
    mappeur.

    Les groupes ne suivent pas les utilisateurs tout seuls. Un second composant
    les projette, et il doit viser la branche des groupes et nommer l'attribut
    d'appartenance que l'annuaire emploie.
    """
    federation = _federation(idp)
    mappeurs = _api(
        idp,
        f"components?parent={federation['id']}"
        "&type=org.keycloak.storage.ldap.mappers.LDAPStorageMapper",
    ) or []

    groupes = [m for m in mappeurs if m.get("providerId") == "group-ldap-mapper"]
    assert groupes, message(
        en="No group mapper on the federation. The accounts would be "
        "imported without their groups, and the provider would know nothing of who "
        "belongs to what. Mappers found: "
        f"{[m.get('providerId') for m in mappeurs]}",
        fr="Aucun mappeur de groupes sur la fédération. Les comptes seraient "
        "importés sans leurs groupes, et le fournisseur ne saurait rien de qui "
        "appartient à quoi. Mappeurs trouvés : "
        f"{[m.get('providerId') for m in mappeurs]}",
    )

    mappeur = groupes[0]
    identifiants = _identifiants(idp)
    attendu = identifiants["GROUPS_DN"]
    lu = _config(mappeur, "groups.dn")
    assert lu == attendu, message(
        en=f"The mapper targets \"{lu}\" instead of \"{attendu}\". It will look for the "
        "groups where there are none.",
        fr=f"Le mappeur vise « {lu} » au lieu de « {attendu} ». Il cherchera les "
        "groupes là où il n'y en a pas.",
    )

    appartenance = _config(mappeur, "membership.ldap.attribute")
    assert appartenance.lower() == "member", message(
        en=f"The mapper reads membership in \"{appartenance}\". This directory "
        "publishes it in `member`, and also in `uniqueMember` and `memberOf`.",
        fr=f"Le mappeur lit l'appartenance dans « {appartenance} ». Cet annuaire "
        "la publie dans `member`, et aussi dans `uniqueMember` et `memberOf`.",
    )


def test_les_groupes_sont_importes_avec_exactement_leurs_membres(idp):
    """L'appartenance, vue du fournisseur, et elle est exacte.

    Vert avant le travail ? Non : le realm n'a aucun groupe, et le nettoyage
    les retire.

    « Exactement » compte : un groupe qui contient une personne de trop accorde
    un droit que personne n'a demandé. Les groupes propres à l'annuaire
    (`lldap_*`) ne sont pas comptés comme des erreurs, ils arrivent avec le
    reste.
    """
    groupes = _groupes_du_realm(idp)

    manquants = sorted(set(GROUPES) - set(groupes))
    assert not manquants, message(
        en=f"The realm does not know the groups {manquants}. Was the mapper "
        "synchronised? Declaring the mapper does not launch the import: it has to "
        f"be triggered. Groups known: {sorted(groupes)}",
        fr=f"Le realm ne connaît pas les groupes {manquants}. Le mappeur a-t-il "
        "été synchronisé ? Déclarer le mappeur ne lance pas l'import : il faut "
        f"le déclencher. Groupes connus : {sorted(groupes)}",
    )

    for nom, attendus in GROUPES.items():
        membres_bruts = _api(idp, f"groups/{groupes[nom]}/members?max=200") or []
        membres = {m["username"] for m in membres_bruts}
        assert membres == attendus, message(
            en=f"The group \"{nom}\" contains {sorted(membres)} instead of "
            f"{sorted(attendus)}. If the group is empty, the mapper reads "
            "membership in the wrong attribute, or its retrieve strategy "
            "does not match what the directory publishes.",
            fr=f"Le groupe « {nom} » contient {sorted(membres)} au lieu de "
            f"{sorted(attendus)}. Si le groupe est vide, le mappeur lit "
            "l'appartenance dans le mauvais attribut, ou sa stratégie de "
            "récupération ne correspond pas à ce que l'annuaire publie.",
        )


def test_un_compte_de_l_annuaire_obtient_un_jeton(idp):
    """La preuve que la fédération sert à quelque chose.

    Vert avant le travail ? Non : le compte n'existe pas dans le realm.

    Tout le reste peut être juste sans que personne puisse se connecter. Ici un
    compte que le fournisseur n'a jamais créé s'authentifie auprès de lui, et
    c'est le seul résultat qui intéresse l'utilisateur.
    """
    identifiants = _identifiants(idp)
    res = idp.run(
        f"curl -sS --max-time 20 -X POST "
        f"{KEYCLOAK}/realms/{REALM}/protocol/openid-connect/token "
        f"-d grant_type=password -d client_id={identifiants['CLIENT_DE_TEST']} "
        "-d scope=openid "
        "-d username=aline "
        f"-d password={identifiants['COMPTES_MOT_DE_PASSE']!r}"
    )
    try:
        reponse = json.loads(res.stdout or "{}")
    except json.JSONDecodeError:
        pytest.fail(message(
            en=f"Unreadable answer from the token endpoint: {res.stdout[:300]}",
            fr=f"Réponse illisible du point de jeton : {res.stdout[:300]}",
        ))

    assert reponse.get("access_token"), message(
        en="The directory's account \"aline\" does not obtain a token on the realm "
        f"({reponse.get('error')}: {reponse.get('error_description')}). Does the "
        "federation really authenticate, or does it merely "
        "import the accounts?",
        fr="Le compte « aline » de l'annuaire n'obtient pas de jeton sur le realm "
        f"({reponse.get('error')} : {reponse.get('error_description')}). La "
        "fédération authentifie-t-elle vraiment, ou se contente-t-elle "
        "d'importer les comptes ?",
    )


def test_le_fournisseur_refuse_de_modifier_un_compte_federe(idp):
    """Le refus réel, et non la case cochée.

    Vert avant le travail ? Non : sans fédération, il n'y a pas de compte
    fédéré à modifier.

    Un mode d'édition posé sans effet laisserait le fournisseur écrire dans
    l'annuaire. Le seul contrôle qui tienne est d'essayer de modifier un compte
    fédéré et de vérifier que le fournisseur refuse. Mesuré le 2026-10-16 : il
    rend `error-user-attribute-read-only`.
    """
    comptes = _comptes_du_realm(idp)
    assert "aline" in comptes, message(
        en="The account \"aline\" is not in the realm: this test cannot "
        "measure. See the synchronisation test.",
        fr="Le compte « aline » n'est pas dans le realm : ce test ne peut pas "
        "mesurer. Voir le test de la synchronisation.",
    )

    jeton = _jeton_admin(idp)
    res = idp.run(
        f"curl -sS --max-time 20 -o /tmp/refus-test -w '%{{http_code}}' "
        f"-X PUT '{KEYCLOAK}/admin/realms/{REALM}/users/{comptes['aline']['id']}' "
        f"-H 'Authorization: Bearer {jeton}' "
        "-H 'Content-Type: application/json' "
        '-d \'{"firstName":"ModifieeParLeTest"}\'; echo; cat /tmp/refus-test'
    )
    morceaux = res.stdout.split("\n", 1)
    code = morceaux[0].strip()
    corps = morceaux[1] if len(morceaux) > 1 else ""

    assert code != "204" and code != "200", message(
        en=f"The provider ACCEPTED modifying a federated account (HTTP {code}). "
        "The federation is therefore not really read-only, and a "
        "correction made in the console would change the directory.",
        fr=f"Le fournisseur a ACCEPTÉ de modifier un compte fédéré (HTTP {code}). "
        "La fédération n'est donc pas réellement en lecture seule, et une "
        "correction faite dans la console changerait l'annuaire.",
    )
    assert "read-only" in corps.lower() or "read_only" in corps.lower(), message(
        en=f"The refusal is not the expected one (HTTP {code}): {corps[:300]}. "
        "Measured on Keycloak 26.8.1, a read-only federation returns "
        "`error-user-attribute-read-only`.",
        fr=f"Le refus n'est pas celui attendu (HTTP {code}) : {corps[:300]}. "
        "Mesuré sur Keycloak 26.8.1, une fédération en lecture seule rend "
        "`error-user-attribute-read-only`.",
    )
