"""Les deux côtés de SAML, et le compte qui arrive au bout.

Aucun test ne lit une assertion XML. Ils regardent ce que chaque côté déclare,
puis ils JOUENT le parcours complet et lisent le compte que le fournisseur de
service a créé. C'est le seul résultat qui prouve que l'assertion est passée,
qu'elle était signée, et qu'elle portait les bons attributs.

CE QUI A ÉTÉ MESURÉ LE 2026-10-16, ET QUI DÉCIDE DE CES TESTS

Le parcours complet traverse huit étapes, dont deux formulaires auto-soumis :
SAML passe par le navigateur sans redirection HTTP, et un outil qui ne les
reposterait pas conclurait que l'intégration s'arrête là.

Les groupes n'arrivent pas tout seuls. Un `saml-group-membership-mapper` côté
émetteur les met dans l'assertion, et il faut un `saml-advanced-group-idp-mapper`
côté consommateur pour y ranger le compte. Mesuré : sans le second, le compte
arrive avec son adresse et sans aucun groupe.

Et `syncMode` décide si un mappeur s'applique à un compte DÉJÀ lié. Sur un
compte existant, un mappeur en `INHERIT` ne réapplique rien, ce qui ressemble
trait pour trait à un mappeur qui ne fonctionne pas.
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
EMETTEUR = "formation"
CONSOMMATEUR = "partenaire-sp"
ALIAS = "saml-formation"
PORT_TEMOIN = 9080
OUTILS = "/opt/iam-lab/outils"
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
    """Un jeton d'administration, obtenu avec le compte du socle.

    Sans `set -o pipefail` : testinfra exécute par `/bin/sh`, qui est `dash`
    sur Ubuntu et répond « set: Illegal option -o pipefail ».
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


def _client_saml(hote) -> dict:
    """Le client SAML, cherché par son identifiant d'entité.

    L'identifiant est une URL : il faut l'encoder pour le passer en paramètre
    de requête, sinon ses `/` et ses `:` cassent le chemin.
    """
    entite = _identifiants(hote)["ENTITE_CONSOMMATEUR"]
    trouves = _api(
        hote,
        f"realms/{EMETTEUR}/clients?clientId={urllib.parse.quote(entite, safe='')}",
    ) or []
    assert trouves, message(
        en=f"No client with identifier \"{entite}\" in the realm "
        f"\"{EMETTEUR}\". The service provider announces itself under that "
        "entity identifier, and that is what the client must carry.",
        fr=f"Aucun client d'identifiant « {entite} » dans le realm "
        f"« {EMETTEUR} ». Le fournisseur de service s'annonce sous cet "
        "identifiant d'entité, et c'est lui que le client doit porter.",
    )
    return trouves[0]


def _attribut(objet: dict, clef: str) -> str:
    return (objet.get("attributes") or {}).get(clef, "")


def _config(objet: dict, clef: str) -> str:
    """Une valeur de `config`, qui peut arriver seule ou en liste.

    Les composants rendent des listes, les fournisseurs d'identité rendent des
    chaînes. Traiter les deux évite un test qui échoue sur la forme.
    """
    valeur = (objet.get("config") or {}).get(clef)
    if isinstance(valeur, list):
        return valeur[0] if valeur else ""
    return valeur or ""


def _fournisseur_d_identite(hote) -> dict:
    trouves = _api(hote, f"realms/{CONSOMMATEUR}/identity-provider/instances") or []
    saml = [i for i in trouves if i.get("providerId") == "saml"]
    assert saml, message(
        en=f"No SAML identity provider in the realm \"{CONSOMMATEUR}\". "
        "That is the consuming half of the work: without it, the service "
        "provider does not know whom to ask for an assertion. Providers "
        f"found: {[i.get('providerId') for i in trouves]}",
        fr=f"Aucun fournisseur d'identité SAML dans le realm « {CONSOMMATEUR} ». "
        "C'est la moitié consommatrice du travail : sans lui, le fournisseur de "
        "service ne sait pas à qui demander une assertion. Fournisseurs "
        f"trouvés : {[i.get('providerId') for i in trouves]}",
    )
    identite = saml[0]
    assert identite.get("alias") == ALIAS, message(
        en=f"The identity provider is named \"{identite.get('alias')}\" instead "
        f"of \"{ALIAS}\". Its alias decides the URL of its reception "
        "endpoint, which the issuer's SAML client must declare, and "
        "the witness application names it in its configuration.",
        fr=f"Le fournisseur d'identité s'appelle « {identite.get('alias')} » au "
        f"lieu de « {ALIAS} ». Son alias décide de l'URL de son point de "
        "réception, que le client SAML de l'émetteur doit déclarer, et "
        "l'application témoin le nomme dans sa configuration.",
    )
    return identite


def _parcours(hote) -> dict:
    identifiants = _identifiants(hote)
    attendu = f"Connecté en tant que {identifiants['UTILISATEUR']}"
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


def _compte_du_consommateur(hote) -> dict | None:
    trouves = _api(
        hote, f"realms/{CONSOMMATEUR}/users?username=alice&exact=true"
    ) or []
    if not trouves:
        return None
    return _api(hote, f"realms/{CONSOMMATEUR}/users/{trouves[0]['id']}")


# ── Les tests ────────────────────────────────────────────────────────────────


def test_le_client_saml_existe_avec_l_identifiant_d_entite_attendu(idp):
    """Un fournisseur de service s'annonce par un identifiant d'entité.

    Vert avant le travail ? Non : le setup retire le client s'il en trouve un.

    L'identifiant d'entité n'est pas un nom qu'on choisit : c'est celui que le
    fournisseur de service publie dans ses métadonnées. Le déclarer autrement
    fait refuser l'assertion, parce que son destinataire ne se reconnaît pas.
    """
    client = _client_saml(idp)

    assert client.get("protocol") == "saml", message(
        en=f"The client exists but speaks \"{client.get('protocol')}\". A "
        "SAML service provider does not consume an OIDC token.",
        fr=f"Le client existe mais parle « {client.get('protocol')} ». Un "
        "fournisseur de service SAML ne consomme pas un jeton OIDC.",
    )
    assert client.get("enabled") is True, message(
        en="The SAML client is disabled: no assertion will come out of it.",
        fr="Le client SAML est désactivé : aucune assertion n'en sortira.",
    )

    identifiants = _identifiants(idp)
    attendu = identifiants["ACS_CONSOMMATEUR"]
    uris = client.get("redirectUris") or []
    assert any(attendu in u for u in uris), message(
        en=f"The client does not declare \"{attendu}\" as its return address "
        f"(declared: {uris}). That is where the service provider expects "
        "the assertion, and an inexact address sends it elsewhere.",
        fr=f"Le client ne déclare pas « {attendu} » comme adresse de retour "
        f"(déclaré : {uris}). C'est là que le fournisseur de service attend "
        "l'assertion, et une adresse inexacte la fait partir ailleurs.",
    )


def test_les_assertions_sont_signees(idp):
    """Une assertion non signée est un document que n'importe qui fabrique.

    Vert avant le travail ? Non : sans client, il n'y a rien à lire.

    C'est le réglage central de SAML. Le consommateur fait confiance à
    l'assertion parce qu'elle porte la signature d'un émetteur dont il connaît
    le certificat. Sans signature, il croirait n'importe quel document qui lui
    arrive sur la bonne adresse.
    """
    client = _client_saml(idp)

    signee = _attribut(client, "saml.assertion.signature")
    assert str(signee).lower() == "true", message(
        en="The assertions are not signed "
        f"(saml.assertion.signature = {signee!r}). The service provider "
        "would then accept a document fabricated by anyone who knows its "
        "return address.",
        fr="Les assertions ne sont pas signées "
        f"(saml.assertion.signature = {signee!r}). Le fournisseur de service "
        "accepterait alors un document fabriqué par quiconque connaît son "
        "adresse de retour.",
    )

    algo = _attribut(client, "saml.signature.algorithm")
    assert algo and "SHA1" not in algo.upper(), message(
        en=f"The signature algorithm is \"{algo or 'undeclared'}\". SHA-1 has been "
        "broken since 2017 and must no longer sign an assertion.",
        fr=f"L'algorithme de signature est « {algo or 'non déclaré'} ». SHA-1 est "
        "cassé depuis 2017 et ne doit plus signer d'assertion.",
    )


def test_l_emetteur_envoie_le_courriel_et_les_groupes(idp):
    """Quatre mappeurs, et aucun n'est décoratif.

    Vert avant le travail ? Non : un client SAML neuf n'a aucun mappeur
    d'attribut.

    Le consommateur ne peut transmettre que ce qu'il reçoit. Un compte qui
    arrive sans adresse force le fournisseur de service à la demander, et le
    parcours s'arrête sur un formulaire de complément de profil.
    """
    client = _client_saml(idp)
    mappeurs = _api(
        idp,
        f"realms/{EMETTEUR}/clients/{client['id']}/protocol-mappers/models",
    ) or []

    types = {m.get("protocolMapper") for m in mappeurs}
    assert "saml-group-membership-mapper" in types, message(
        en="No group membership mapper. The assertion will not carry "
        f"the groups, and the consumer will not be able to file them. Mappers "
        f"present: {sorted(types)}",
        fr="Aucun mappeur d'appartenance aux groupes. L'assertion ne portera pas "
        f"les groupes, et le consommateur ne pourra pas les ranger. Mappeurs "
        f"présents : {sorted(types)}",
    )

    attributs = {
        (m.get("config") or {}).get("attribute.name")
        for m in mappeurs
        if m.get("protocolMapper") != "saml-group-membership-mapper"
    }
    proprietes = {
        (m.get("config") or {}).get("user.attribute")
        for m in mappeurs
    }
    assert "email" in proprietes, message(
        en="No mapper projects the account's mail address "
        f"(properties projected: {sorted(p for p in proprietes if p)}). The "
        "consumer will have to ask the user for it.",
        fr="Aucun mappeur ne projette l'adresse de courriel du compte "
        f"(propriétés projetées : {sorted(p for p in proprietes if p)}). Le "
        "consommateur devra la demander à l'utilisateur.",
    )
    assert {"firstName", "lastName"} <= proprietes, message(
        en="The first name and the surname are not both projected "
        f"(properties: {sorted(p for p in proprietes if p)}). Measured on "
        "2026-10-16: without them, the consumer stops on \"Update Account "
        "Information\" and the login never completes.",
        fr="Le prénom et le nom ne sont pas tous les deux projetés "
        f"(propriétés : {sorted(p for p in proprietes if p)}). Mesuré le "
        "2026-10-16 : sans eux, le consommateur s'arrête sur « Update Account "
        "Information » et la connexion n'aboutit jamais.",
    )
    assert attributs, message(
        en="The attribute mappers name no attribute.",
        fr="Les mappeurs d'attribut ne nomment aucun attribut.",
    )


def test_le_consommateur_valide_la_signature_de_l_emetteur(idp):
    """Exiger une assertion signée ET vérifier la signature.

    Vert avant le travail ? Non : il n'y a pas de fournisseur d'identité.

    Les deux réglages sont distincts et tous deux nécessaires. Exiger la
    signature sans la vérifier revient à demander un sceau sans regarder lequel.
    """
    identite = _fournisseur_d_identite(idp)

    assert identite.get("enabled") is True, message(
        en="The identity provider is declared but disabled.",
        fr="Le fournisseur d'identité est déclaré mais désactivé.",
    )
    assert _config(identite, "wantAssertionsSigned") == "true", message(
        en="The consumer does not require the assertions to be signed "
        f"(wantAssertionsSigned = {_config(identite, 'wantAssertionsSigned')!r}).",
        fr="Le consommateur n'exige pas que les assertions soient signées "
        f"(wantAssertionsSigned = {_config(identite, 'wantAssertionsSigned')!r}).",
    )
    assert _config(identite, "validateSignature") == "true", message(
        en="The consumer does not verify the signature "
        f"(validateSignature = {_config(identite, 'validateSignature')!r}). "
        "Requiring a seal without looking at it protects nothing.",
        fr="Le consommateur ne vérifie pas la signature "
        f"(validateSignature = {_config(identite, 'validateSignature')!r}). "
        "Exiger un sceau sans le regarder ne protège de rien.",
    )

    certificat = _config(identite, "signingCertificate")
    assert certificat and len(certificat) > 200, message(
        en="No signing certificate is declared on the consumer's side, or it "
        f"is too short to be one ({len(certificat)} characters). It is "
        "read in the issuer's metadata, published at the address "
        "given in identifiants-lab.txt.",
        fr="Aucun certificat de signature n'est déclaré côté consommateur, ou il "
        f"est trop court pour en être un ({len(certificat)} caractères). Il se "
        "lit dans les métadonnées de l'émetteur, qui sont publiées à l'adresse "
        "donnée dans identifiants-lab.txt.",
    )

    emetteur_attendu = f"{KEYCLOAK}/realms/{EMETTEUR}"
    lu = _config(identite, "idpEntityId")
    assert lu == emetteur_attendu, message(
        en=f"The consumer expects assertions from \"{lu}\" instead of "
        f"\"{emetteur_attendu}\". It will refuse those coming from the right "
        "issuer.",
        fr=f"Le consommateur attend des assertions de « {lu} » au lieu de "
        f"« {emetteur_attendu} ». Il refusera celles qui viennent du bon "
        "émetteur.",
    )


def test_le_parcours_complet_connecte_l_utilisateur(idp):
    """LE TEST CENTRAL : l'utilisateur arrive connecté, par SAML.

    Vert avant le travail ? Non : sans les deux côtés, le parcours s'arrête
    chez le consommateur.

    Tous les réglages précédents peuvent être justes sans que personne ne passe.
    Ici un compte de l'émetteur traverse le protocole entier et l'application
    affiche son nom. Le parcours franchit deux formulaires auto-soumis, qui est
    la façon dont SAML traverse un navigateur sans redirection HTTP.
    """
    etat = idp.run(f"curl -sS --max-time 10 http://127.0.0.1:{PORT_TEMOIN}/etat")
    assert etat.rc == 0 and etat.stdout.strip(), message(
        en=f"The witness application does not answer on port {PORT_TEMOIN}. The "
        "setup starts it: if it is absent, its log is in "
        "/opt/iam-lab/appli-temoin/temoin.log.",
        fr=f"L'application témoin ne répond pas sur le port {PORT_TEMOIN}. Le "
        "setup la démarre : si elle est absente, son journal est dans "
        "/opt/iam-lab/appli-temoin/temoin.log.",
    )

    resultat = _parcours(idp)

    assert resultat.get("connexion_posee") is True, message(
        en="The journey never met a login form. "
        "The application was therefore not taken as far as the issuer: it "
        f"stopped on {resultat.get('arrivee')}.",
        fr="Le parcours n'a jamais rencontré de formulaire de connexion. "
        "L'application n'a donc pas été emmenée jusqu'à l'émetteur : elle "
        f"s'est arrêtée sur {resultat.get('arrivee')}.",
    )
    assert resultat.get("texte_trouve") is True, message(
        en="The landing page does not show the logged-in user. The journey "
        f"ended on {resultat.get('arrivee')} "
        f"(HTTP {resultat.get('http')}) with: "
        f"{str(resultat.get('texte'))[:300]}\n\n"
        "If you read \"Update Account Information\", the assertion did not "
        "carry everything the consumer requires to create an account without "
        "asking: address, first name and surname.",
        fr="La page d'arrivée n'affiche pas l'utilisateur connecté. Le parcours "
        f"s'est terminé sur {resultat.get('arrivee')} "
        f"(HTTP {resultat.get('http')}) avec : "
        f"{str(resultat.get('texte'))[:300]}\n\n"
        "Si vous lisez « Update Account Information », l'assertion n'a pas "
        "porté tout ce que le consommateur exige pour créer un compte sans "
        "demander : adresse, prénom et nom.",
    )


def test_le_compte_arrive_avec_son_courriel_et_son_identite(idp):
    """Ce que le consommateur a vraiment reçu, lu sur le compte qu'il a créé.

    Vert avant le travail ? Non : le realm consommateur est recréé vide par le
    setup.
    """
    compte = _compte_du_consommateur(idp)
    assert compte, message(
        en=f"The realm \"{CONSOMMATEUR}\" has no \"alice\" account. Did the journey "
        "complete? See the previous test.",
        fr=f"Le realm « {CONSOMMATEUR} » n'a aucun compte « alice ». Le parcours "
        "a-t-il abouti ? Voir le test précédent.",
    )

    assert compte.get("email") == "aline@formation.lab", message(
        en=f"The account carries the address {compte.get('email')!r} instead of "
        "'aline@formation.lab'. Did the assertion carry it, and does the "
        "consumer have a mapper to read it?",
        fr=f"Le compte porte l'adresse {compte.get('email')!r} au lieu de "
        "'aline@formation.lab'. L'assertion la portait-elle, et le "
        "consommateur a-t-il un mappeur pour la lire ?",
    )
    assert compte.get("firstName") == "Aline", message(
        en=f"The first name read is {compte.get('firstName')!r} instead of 'Aline'.",
        fr=f"Le prénom lu est {compte.get('firstName')!r} au lieu de 'Aline'.",
    )
    assert compte.get("lastName") == "Dupont", message(
        en=f"The surname read is {compte.get('lastName')!r} instead of 'Dupont'.",
        fr=f"Le nom lu est {compte.get('lastName')!r} au lieu de 'Dupont'.",
    )

    liens = _api(
        idp,
        f"realms/{CONSOMMATEUR}/users/{compte['id']}/federated-identity",
    ) or []
    alias = {li.get("identityProvider") for li in liens}
    assert ALIAS in alias, message(
        en=f"The account is not linked to the identity provider \"{ALIAS}\" "
        f"(links: {sorted(a for a in alias if a)}). It was created by hand, "
        "and it will not follow the issuer.",
        fr=f"Le compte n'est pas lié au fournisseur d'identité « {ALIAS} » "
        f"(liens : {sorted(a for a in alias if a)}). Il a été créé à la main, "
        "et il ne suivra pas l'émetteur.",
    )


def test_les_groupes_de_l_assertion_rangent_le_compte(idp):
    """Les groupes, qui n'arrivent pas tout seuls.

    Vert avant le travail ? Non : le compte n'existe pas.

    Mesuré le 2026-10-16 : un mappeur d'appartenance côté émetteur met les
    groupes dans l'assertion, et le compte arrive quand même SANS aucun groupe.
    Il faut un second mappeur côté consommateur pour y ranger le compte, et le
    groupe doit préexister dans son realm, un mappeur ne le créant pas.
    """
    compte = _compte_du_consommateur(idp)
    assert compte, message(
        en=f"The realm \"{CONSOMMATEUR}\" has no \"alice\" account.",
        fr=f"Le realm « {CONSOMMATEUR} » n'a aucun compte « alice ».",
    )

    identifiants = _identifiants(idp)
    attendu = identifiants["GROUPE"]
    groupes = _api(
        idp, f"realms/{CONSOMMATEUR}/users/{compte['id']}/groups"
    ) or []
    noms = {g["name"] for g in groupes}

    assert attendu in noms, message(
        en=f"The account is not in the group \"{attendu}\" on the consumer's side "
        f"(groups: {sorted(noms)}).\n\n"
        "The assertion can carry the groups without the consumer filing "
        "them: it needs a mapper that reads the attribute and names the "
        "group. Mind `syncMode` too: on an ALREADY linked account, a "
        "mapper set to `INHERIT` reapplies nothing, which looks exactly "
        "like a mapper that does not work.",
        fr=f"Le compte n'est pas dans le groupe « {attendu} » côté consommateur "
        f"(groupes : {sorted(noms)}).\n\n"
        "L'assertion peut porter les groupes sans que le consommateur les "
        "range : il lui faut un mappeur qui lit l'attribut et désigne le "
        "groupe. Attention aussi à `syncMode` : sur un compte DÉJÀ lié, un "
        "mappeur en `INHERIT` ne réapplique rien, ce qui ressemble trait pour "
        "trait à un mappeur qui ne fonctionne pas.",
    )
