"""L'état de l'annuaire, interrogé par ldapsearch.

Aucun test ne regarde comment les comptes ont été créés. Ils interrogent
l'annuaire, ce qui est la seule chose qu'un fournisseur d'identité fera ensuite.

CE QUE LA MESURE A APPRIS SUR LLDAP 0.6.3, ET QUI DÉCIDE DE CES TESTS

LLDAP sert le LDAP en lecture, et accepte une PARTIE des écritures :

    ldapadd d'un compte          accepté
    ldapadd d'un groupe          accepté, mais son `member:` est IGNORÉ
    ldapmodify add: member       REFUSÉ, « Invalid DN syntax (34) »
    ldappasswd                   accepté
    addUserToGroup par l'API     accepté, et c'est la seule voie

Mesuré le 2026-10-16. Les tests vérifient donc l'APPARTENANCE, sans rien
imposer sur la façon de l'avoir posée : `memberOf`, `member` et `uniquemember`
sont tous les trois servis une fois l'appartenance en place.
"""

from __future__ import annotations

import base64

import pytest

from conftest import lab_host, lab_target_host

# L'hôte RÉELLEMENT testé. `dsoxlab check --target` peut en imposer un autre,
# et coder le nom en dur ferait tester la cible par défaut en prétendant tester
# celle qu'on a demandée.
CIBLE = lab_target_host("idp.lab")

IDENTIFIANTS = "/opt/iam-lab/identifiants-lab.txt"
CONTENEUR_ANNUAIRE = "socle-iam-lldap-1"

#: Les trois personnes attendues, avec leur nom affiché et leur adresse.
PERSONNES = {
    "aline": ("Aline Dupont", "aline@formation.lab"),
    "bruno": ("Bruno Keller", "bruno@formation.lab"),
    "chloe": ("Chloé Nguyen", "chloe@formation.lab"),
}

#: Les deux groupes, et qui doit en être membre.
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


def _chercher(hote, base: str, filtre: str, *attributs: str) -> str:
    """Une requête ldapsearch, rendue telle quelle.

    `partition` et non `cut -d= -f2` pour lire les identifiants : le DN de base
    vaut `dc=formation,dc=lab`, et `cut -d= -f2` le couperait au premier `=` en
    rendant `dc`. Toutes les requêtes échoueraient alors sur « Naming violation
    (64) : Missing DN value », ce qui désigne la requête et non la variable qui
    l'a fabriquée.
    """
    identifiants = _identifiants(hote)
    demandes = " ".join(attributs)
    res = hote.run(
        f"ldapsearch -x -H {identifiants['LDAP_URL']} "
        f"-D {identifiants['ADMIN_DN']!r} "
        f"-w {identifiants['ADMIN_MOT_DE_PASSE']!r} "
        f"-b {base!r} -LLL {filtre!r} {demandes}"
    )
    assert res.rc in (0, 4), (
        f"La requête LDAP a échoué (rc={res.rc}). L'annuaire répond-il ? "
        f"Sortie : {(res.stdout + res.stderr)[:400]}"
    )
    return res.stdout


def _valeurs(sortie: str, attribut: str) -> list[str]:
    """Les valeurs d'un attribut dans une sortie LDIF.

    Deux subtilités du format, et les deux ont coûté un passage.

    LLDAP rend les noms d'attributs en MINUSCULES (`memberof`, `uniquemember`)
    là où la requête les écrit en casse mixte. Comparer la casse ferait échouer
    un test sur une différence qui n'en est pas une.

    Et surtout, LDIF encode en BASE64 toute valeur qui n'est pas de l'ASCII
    imprimable, en le signalant par un DOUBLE deux-points :

        cn: Bruno Keller
        cn:: Q2hsb8OpIE5ndXllbg==      (« Chloé Nguyen »)

    Mesuré le 2026-10-16 : le test échouait sur « cn lu :
    [': Q2hsb8OpIE5ndXllbg=='] », ce qui ressemble à un compte mal créé alors
    que le compte est juste. Un annuaire d'entreprise est plein d'accents : un
    lecteur de LDIF qui ne décode pas est un lecteur qui mentira tôt ou tard.
    """
    trouvees = []
    for ligne in sortie.splitlines():
        if ":" not in ligne:
            continue
        nom, _, reste = ligne.partition(":")
        if nom.strip().lower() != attribut.lower():
            continue
        if reste.startswith(":"):
            # Double deux-points : la valeur est en base64.
            try:
                trouvees.append(
                    base64.b64decode(reste[1:].strip()).decode("utf-8")
                )
            except (ValueError, UnicodeDecodeError):
                trouvees.append(reste[1:].strip())
        else:
            trouvees.append(reste.strip())
    return trouvees


def _base(hote) -> str:
    return _identifiants(hote)["BASE_DN"]


# ── Les tests ────────────────────────────────────────────────────────────────


def test_l_annuaire_repond_et_le_compte_d_administration_se_lie(idp):
    """Avant de juger le travail, vérifier que l'annuaire sert.

    Vert avant le travail ? OUI, et c'est assumé : l'annuaire fait partie du
    socle. Ce test n'note pas le travail, il évite que les cinq autres
    échouent sans dire si c'est la configuration ou le service qui manque.
    """
    identifiants = _identifiants(idp)
    res = idp.run(
        f"ldapwhoami -x -H {identifiants['LDAP_URL']} "
        f"-D {identifiants['ADMIN_DN']!r} "
        f"-w {identifiants['ADMIN_MOT_DE_PASSE']!r}"
    )
    assert res.rc == 0, (
        f"Le compte d'administration ne se lie pas à l'annuaire (rc={res.rc}). "
        f"Sortie : {(res.stdout + res.stderr)[:300]}"
    )
    assert identifiants["ADMIN_DN"] in res.stdout, (
        f"La liaison réussit mais l'annuaire rend une identité inattendue : "
        f"{res.stdout.strip()[:200]}"
    )


@pytest.mark.parametrize("compte", sorted(PERSONNES))
def test_chaque_personne_existe_avec_son_nom_et_son_adresse(idp, compte):
    """Un compte sans nom affiché ni adresse ne sert à rien en aval.

    Vert avant le travail ? Non : le setup retire les trois comptes.

    Le fournisseur d'identité qui lira cet annuaire a besoin du nom pour
    l'afficher et de l'adresse pour écrire aux gens. Un compte réduit à son
    identifiant force à aller chercher l'information ailleurs, ce qui est
    exactement ce qu'un annuaire doit éviter.
    """
    nom_attendu, adresse_attendue = PERSONNES[compte]
    base = _base(idp)
    sortie = _chercher(idp, f"ou=people,{base}", f"(uid={compte})", "cn", "mail", "sn")

    assert f"uid={compte},ou=people,{base}" in sortie, (
        f"Le compte « {compte} » n'existe pas sous ou=people,{base}. LLDAP "
        "impose cette branche : il n'accepte pas d'unité d'organisation que "
        "vous auriez créée ailleurs."
    )

    noms = _valeurs(sortie, "cn")
    assert nom_attendu in noms, (
        f"Le compte « {compte} » n'a pas « {nom_attendu} » comme nom affiché "
        f"(cn lu : {noms}). C'est ce que le fournisseur d'identité affichera."
    )

    adresses = _valeurs(sortie, "mail")
    assert adresse_attendue in adresses, (
        f"Le compte « {compte} » n'a pas « {adresse_attendue} » comme adresse "
        f"(mail lu : {adresses})."
    )


@pytest.mark.parametrize("groupe", sorted(GROUPES))
def test_chaque_groupe_existe_avec_exactement_ses_membres(idp, groupe):
    """L'appartenance, et elle est exacte : ni en moins, ni en trop.

    Vert avant le travail ? Non : le setup retire les deux groupes.

    « Ni en trop » compte autant que « ni en moins ». Un groupe qui contient
    une personne de plus accorde un droit que personne n'a demandé, et c'est
    précisément ce qu'une revue d'accès cherche des mois plus tard.
    """
    base = _base(idp)
    attendus = {
        f"uid={compte},ou=people,{base}" for compte in GROUPES[groupe]
    }

    sortie = _chercher(
        idp, f"ou=groups,{base}", f"(cn={groupe})", "member", "uniqueMember"
    )
    assert f"cn={groupe},ou=groups,{base}" in sortie, (
        f"Le groupe « {groupe} » n'existe pas sous ou=groups,{base}."
    )

    membres = set(_valeurs(sortie, "member")) | set(_valeurs(sortie, "uniquemember"))

    manquants = attendus - membres
    assert not manquants, (
        f"Le groupe « {groupe} » ne contient pas {sorted(manquants)}.\n\n"
        "ATTENTION, c'est le piège de ce lab : LLDAP ACCEPTE un `ldapadd` de "
        "groupe qui déclare `member:`, et IGNORE ce membre en silence. Un "
        "`ldapmodify add: member` est refusé avec « Invalid DN syntax ». "
        "L'appartenance se pose par l'API de l'annuaire. "
        f"Membres lus : {sorted(membres)}"
    )

    en_trop = membres - attendus
    assert not en_trop, (
        f"Le groupe « {groupe} » contient en plus {sorted(en_trop)}. Un droit "
        "accordé à quelqu'un qui ne l'a pas demandé est exactement ce qu'une "
        "revue d'accès cherche des mois plus tard."
    )


def test_l_appartenance_se_lit_aussi_depuis_le_compte(idp):
    """`memberOf`, qui est ce qu'un fournisseur d'identité interroge.

    Vert avant le travail ? Non : sans groupes, aucun compte n'a de `memberOf`.

    Le test précédent lit l'appartenance depuis le groupe. Celui-ci la lit
    depuis le compte, et ce n'est pas la même chose : c'est `memberOf` que
    Keycloak lira au lab suivant pour importer les groupes. Mesuré le
    2026-10-16 : LLDAP sert bien `memberOf` une fois l'appartenance posée.
    """
    base = _base(idp)
    for compte, groupes_attendus in (
        ("aline", {"devops"}),
        ("bruno", {"devops", "lecteurs"}),
        ("chloe", {"lecteurs"}),
    ):
        sortie = _chercher(idp, f"ou=people,{base}", f"(uid={compte})", "memberOf")
        lus = {
            valeur.split(",")[0].removeprefix("cn=")
            for valeur in _valeurs(sortie, "memberOf")
        }
        assert lus == groupes_attendus, (
            f"Le compte « {compte} » appartient à {sorted(lus)} au lieu de "
            f"{sorted(groupes_attendus)}. C'est `memberOf` que le fournisseur "
            "d'identité lira pour importer les groupes."
        )


def test_un_filtre_sur_l_appartenance_rend_les_bonnes_personnes(idp):
    """La requête qu'une application écrira vraiment.

    Vert avant le travail ? Non : le filtre ne rendrait personne.

    Une application ne demande pas « qui est dans ce groupe » en lisant le
    groupe : elle filtre les comptes sur leur appartenance. Si ce filtre ne
    fonctionne pas, l'annuaire est juste et inutilisable.
    """
    base = _base(idp)
    sortie = _chercher(
        idp,
        f"ou=people,{base}",
        f"(memberOf=cn=devops,ou=groups,{base})",
        "uid",
    )
    trouves = set(_valeurs(sortie, "uid"))
    assert trouves == GROUPES["devops"], (
        f"Le filtre sur l'appartenance à « devops » rend {sorted(trouves)} au "
        f"lieu de {sorted(GROUPES['devops'])}."
    )


def test_les_donnees_survivent_au_redemarrage_du_conteneur(idp):
    """Le seul contrôle qui distingue un annuaire d'une illusion.

    Vert avant le travail ? Non : il n'y a rien à faire survivre.

    Un annuaire qui perd ses comptes au premier arrêt n'est pas un annuaire.
    Ce test redémarre VRAIMENT le conteneur et relit, parce qu'un volume
    déclaré ne prouve pas qu'il est monté là où les données s'écrivent.
    """
    base = _base(idp)
    avant = set(_valeurs(_chercher(idp, f"ou=people,{base}", "(objectClass=*)", "uid"), "uid"))
    assert PERSONNES.keys() <= avant, (
        f"Les trois comptes ne sont pas tous là avant le redémarrage : {sorted(avant)}"
    )

    redemarrage = idp.run(f"docker restart {CONTENEUR_ANNUAIRE}")
    assert redemarrage.rc == 0, (
        f"Le conteneur de l'annuaire n'a pas redémarré (rc={redemarrage.rc}) : "
        f"{redemarrage.stderr.strip()[:300]}"
    )

    # Sur l'ÉTAT du port, pas sur un délai fixe : LLDAP met de une à dix
    # secondes à servir selon la charge, et un `sleep` calibré sur une machine
    # au repos échoue sur une machine occupée.
    attente = idp.run(
        "for _ in $(seq 1 60); do "
        "if timeout 2 bash -c 'echo > /dev/tcp/127.0.0.1/3890' 2>/dev/null; "
        "then echo pret; break; fi; sleep 1; done"
    )
    assert "pret" in attente.stdout, (
        "L'annuaire n'a pas rouvert son port LDAP dans la minute qui a suivi "
        "son redémarrage."
    )

    apres = set(_valeurs(_chercher(idp, f"ou=people,{base}", "(objectClass=*)", "uid"), "uid"))
    perdus = avant - apres
    assert not perdus, (
        f"Le redémarrage a fait disparaître {sorted(perdus)}. Les données de "
        "l'annuaire ne sont pas persistées : un volume est-il monté là où "
        "elles s'écrivent ?"
    )
