"""Ce que l'API refuse, mesuré en l'appelant pour de vrai.

Aucun test n'ouvre le code de l'API. Ils lui envoient des jetons et lisent sa
réponse, ce qui est la seule façon de distinguer une API qui vérifie d'une API
qui fait semblant.

LE JETON QUI DÉCIDE DE TOUT

Le setup pose une seconde API, `autre-api`, et son scope `autre:lecture` qui
porte son audience. Un jeton demandé avec ce scope est PARFAITEMENT SIGNÉ par
le bon fournisseur, dans le bon realm, et destiné à quelqu'un d'autre.

Mesuré le 2026-10-16 : l'API de départ rend 200 sur ce jeton. C'est tout le
sujet du lab, et c'est le genre de faille qu'aucun essai manuel ne révèle,
parce que le flux normal fonctionne parfaitement.

CE QUE CES TESTS NE MESURENT PAS, ET POURQUOI C'EST DIT

Un jeton d'un AUTRE REALM est déjà refusé par l'API de départ, avec « Unable to
find a signing key that matches ». Ce n'est pas une vérification de l'émetteur :
c'est que le JWKS interrogé est celui du realm attendu, donc la clé de l'autre
realm n'y figure pas. En faire un test laisserait croire que `iss` est vérifié
alors que rien ne le prouve. La solution vérifie `iss` parce que c'est juste, et
aucun test ne prétend le démontrer.
"""

from __future__ import annotations

import base64
import json

import pytest

from conftest import lab_host, lab_target_host

# L'hôte RÉELLEMENT testé. `dsoxlab check --target` peut en imposer un autre,
# et coder le nom en dur ferait tester la cible par défaut en prétendant tester
# celle qu'on a demandée.
CIBLE = lab_target_host("idp.lab")

KEYCLOAK = "http://127.0.0.1:8080"
REALM = "formation"
API = "http://127.0.0.1:8090"
API_CLIENT = "notes-api"
SERVICE = "service-sauvegarde"
SCOPE_LECTURE = "notes:lecture"
SCOPE_ECRITURE = "notes:ecriture"
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
    """Un jeton d'administration, obtenu avec le compte du socle.

    Sans `set -o pipefail` : testinfra exécute par `/bin/sh`, qui est `dash`
    sur Ubuntu et répond « set: Illegal option -o pipefail ». Le résultat est
    vérifié juste après, ce qui vaut mieux qu'un code de retour de tube.
    """
    res = hote.run(
        f"u=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME:' {SECRETS_DU_SOCLE} | cut -d'\"' -f2); "
        f"p=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD:' {SECRETS_DU_SOCLE} | cut -d'\"' -f2); "
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


def _api_admin(hote, chemin: str) -> object:
    jeton = _jeton_admin(hote)
    res = hote.run(
        f"curl -sS --max-time 20 '{KEYCLOAK}/admin/realms/{REALM}/{chemin}' "
        f"-H 'Authorization: Bearer {jeton}'"
    )
    try:
        return json.loads(res.stdout or "null")
    except json.JSONDecodeError:
        pytest.fail(
            f"L'API d'administration n'a pas rendu de JSON pour {chemin} : "
            f"{res.stdout[:300]}"
        )


def _client_declare(hote, nom: str) -> dict:
    trouves = _api_admin(hote, f"clients?clientId={nom}")
    assert trouves, (
        f"Aucun client « {nom} » dans le realm « {REALM} ». C'est l'un des "
        "objets que le challenge demande de déclarer."
    )
    return trouves[0]


def _scope_declare(hote, nom: str) -> dict:
    tous = _api_admin(hote, "client-scopes") or []
    trouves = [s for s in tous if s.get("name") == nom]
    assert trouves, (
        f"Aucun scope de client « {nom} » dans le realm. Les permissions de "
        "l'API se déclarent comme des scopes, un par permission."
    )
    return trouves[0]


def _jeton_utilisateur(hote, scope: str = "") -> str:
    """Un jeton obtenu par le client de test, avec le scope demandé."""
    identifiants = _identifiants(hote)
    option = f" -d scope={scope!r}" if scope else ""
    res = hote.run(
        f"curl -sS --max-time 20 -X POST "
        f"{KEYCLOAK}/realms/{REALM}/protocol/openid-connect/token "
        f"-d grant_type=password -d client_id={identifiants['CLIENT_DE_TEST']} "
        f"-d username={identifiants['UTILISATEUR']} "
        f"-d password={identifiants['MOT_DE_PASSE']!r}{option} "
        "| jq -r '.access_token // empty'"
    )
    jeton = res.stdout.strip()
    assert jeton, (
        f"Aucun jeton obtenu pour le scope {scope!r}. Le scope existe-t-il, et "
        "est-il attaché au client de test ? "
        f"(rc={res.rc}, stderr={res.stderr.strip()[:200]})"
    )
    return jeton


def _jeton_du_service(hote) -> str:
    """Un jeton du service de sauvegarde, en client credentials.

    Le secret est lu par l'API d'administration, et non dans un fichier : le
    challenge interdit justement de l'écrire quelque part.
    """
    client = _client_declare(hote, SERVICE)
    secret = _api_admin(hote, f"clients/{client['id']}/client-secret")
    valeur = (secret or {}).get("value", "")
    assert valeur, (
        f"Le client « {SERVICE} » n'a pas de secret. Un accès machine sans "
        "utilisateur passe par un client CONFIDENTIEL, qui s'authentifie avec "
        "son secret."
    )
    res = hote.run(
        f"curl -sS --max-time 20 -X POST "
        f"{KEYCLOAK}/realms/{REALM}/protocol/openid-connect/token "
        f"-d grant_type=client_credentials -d client_id={SERVICE} "
        f"-d client_secret={valeur!r} | jq -r '.access_token // empty'"
    )
    jeton = res.stdout.strip()
    assert jeton, (
        f"Le client « {SERVICE} » n'obtient pas de jeton en client "
        "credentials. Son compte de service est-il activé ? "
        f"(rc={res.rc})"
    )
    return jeton


def _appeler(hote, methode: str, jeton: str | None = None) -> tuple[int, str, str]:
    """Appelle l'API et rend (code HTTP, corps, en-têtes)."""
    autorisation = f" -H 'Authorization: Bearer {jeton}'" if jeton else ""
    res = hote.run(
        f"curl -sS --max-time 20 -D /tmp/entetes-test -o /tmp/corps-test "
        f"-w '%{{http_code}}' -X {methode} {API}/notes{autorisation}; "
        "echo; cat /tmp/corps-test; echo; cat /tmp/entetes-test"
    )
    morceaux = res.stdout.split("\n", 2)
    assert morceaux and morceaux[0].strip().isdigit(), (
        f"L'API ne répond pas sur {API}. Tourne-t-elle ? "
        f"(rc={res.rc}, sortie={res.stdout[:200]})"
    )
    code = int(morceaux[0].strip())
    corps = morceaux[1] if len(morceaux) > 1 else ""
    entetes = morceaux[2] if len(morceaux) > 2 else ""
    return code, corps, entetes


def _revendications(jeton: str) -> dict:
    """Les revendications d'un JWT, sans vérifier sa signature.

    Sans danger ici : le jeton vient d'être obtenu du serveur par le test
    lui-même. On lit ce qu'il contient, on ne lui accorde aucune confiance.
    """
    charge = jeton.split(".")[1]
    charge += "=" * (-len(charge) % 4)
    return json.loads(base64.urlsafe_b64decode(charge))


# ── Les tests ────────────────────────────────────────────────────────────────


def test_sans_jeton_l_api_refuse_et_dit_comment_s_authentifier(idp):
    """401 et `WWW-Authenticate: Bearer`.

    Vert avant le travail ? OUI, et c'est assumé : l'API de départ refuse déjà
    un appel sans jeton. Ce test n'est pas là pour noter ce refus, il est là
    pour prouver que l'API TOURNE. Sans lui, les six autres échoueraient sans
    qu'on sache si c'est la configuration ou le service qui manque.
    """
    code, corps, entetes = _appeler(idp, "GET")

    assert code == 401, (
        f"Un appel sans jeton rend HTTP {code} au lieu de 401. Une API "
        f"protégée refuse d'abord, elle ne répond pas. Corps : {corps[:200]}"
    )
    assert "www-authenticate" in entetes.lower(), (
        "La réponse ne porte pas d'en-tête `WWW-Authenticate`. La RFC 6750 le "
        "demande : c'est ainsi qu'un client apprend COMMENT s'authentifier, au "
        "lieu de deviner."
    )


def test_le_scope_de_lecture_existe_et_porte_l_audience_de_l_api(idp):
    """Un scope seul ne change pas l'audience : il lui faut un mappeur.

    Vert avant le travail ? Non : le scope n'existe pas, le setup le retire.

    C'est le point le moins intuitif du lab. Déclarer un scope `notes:lecture`
    ne met rien dans `aud`. L'audience arrive par un mappeur de protocole,
    `oidc-audience-mapper`, qui nomme le client visé.
    """
    scope = _scope_declare(idp, SCOPE_LECTURE)

    inclus = (scope.get("attributes") or {}).get("include.in.token.scope")
    assert str(inclus).lower() == "true", (
        f"Le scope « {SCOPE_LECTURE} » n'est pas inclus dans la revendication "
        f"`scope` du jeton (include.in.token.scope = {inclus!r}). L'API ne "
        "pourra donc pas le voir, même quand il est accordé."
    )

    mappeurs = scope.get("protocolMappers") or []
    audiences = [
        m for m in mappeurs
        if m.get("protocolMapper") == "oidc-audience-mapper"
        and (m.get("config") or {}).get("included.client.audience") == API_CLIENT
    ]
    assert audiences, (
        f"Le scope « {SCOPE_LECTURE} » ne porte aucun mappeur d'audience vers "
        f"« {API_CLIENT} ». Un scope seul ne change pas `aud` : sans ce "
        "mappeur, les jetons restent destinés à `account` et l'API ne peut "
        "pas savoir qu'ils sont pour elle. Mappeurs trouvés : "
        f"{[m.get('protocolMapper') for m in mappeurs]}"
    )
    config = audiences[0].get("config") or {}
    assert str(config.get("access.token.claim")).lower() == "true", (
        "Le mappeur d'audience n'écrit pas dans l'access token "
        f"(access.token.claim = {config.get('access.token.claim')!r}). C'est "
        "pourtant ce jeton que l'API reçoit."
    )


def test_un_jeton_de_la_bonne_audience_et_du_bon_scope_est_accepte(idp):
    """Le cas nominal, et il doit marcher : refuser tout n'est pas protéger.

    Vert avant le travail ? Non : sans le scope, aucun jeton ne peut porter la
    bonne audience.
    """
    jeton = _jeton_utilisateur(idp, f"openid {SCOPE_LECTURE}")
    revendications = _revendications(jeton)

    audience = revendications.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    assert API_CLIENT in audiences, (
        f"Le jeton obtenu avec le scope « {SCOPE_LECTURE} » ne porte pas "
        f"l'audience « {API_CLIENT} » (aud = {audience!r}). Le mappeur "
        "d'audience du scope est-il en place ?"
    )
    assert SCOPE_LECTURE in (revendications.get("scope") or "").split(), (
        f"Le jeton ne porte pas « {SCOPE_LECTURE} » dans sa revendication "
        f"`scope` (scope = {revendications.get('scope')!r})."
    )

    code, corps, _ = _appeler(idp, "GET", jeton)
    assert code == 200, (
        f"L'API refuse un jeton de la bonne audience et du bon scope "
        f"(HTTP {code}). Elle est devenue trop stricte, et une API qui refuse "
        f"tout ne protège rien. Corps : {corps[:300]}"
    )


def test_un_jeton_destine_a_une_autre_api_est_refuse(idp):
    """LE COEUR DU LAB.

    Vert avant le travail ? Non, et c'est mesuré : l'API de départ rend 200 sur
    ce jeton.

    Le jeton est parfaitement signé, par le bon fournisseur, dans le bon realm,
    pour le bon utilisateur. Il est simplement destiné à une autre API. Une API
    qui ne vérifie que la signature l'accepte, et le flux normal continue de
    fonctionner : rien ne se voit jamais.
    """
    identifiants = _identifiants(idp)
    jeton = _jeton_utilisateur(idp, f"openid {identifiants['SCOPE_AUTRE_API']}")

    revendications = _revendications(jeton)
    audience = revendications.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    assert identifiants["AUTRE_API"] in audiences, (
        "Le test ne peut pas mesurer : le jeton obtenu ne porte pas "
        f"l'audience de l'autre API (aud = {audience!r}). C'est l'outillage du "
        "lab qui est en cause, pas votre travail."
    )
    assert API_CLIENT not in audiences, (
        "Le test ne peut pas mesurer : ce jeton porte AUSSI l'audience de "
        f"l'API du lab (aud = {audience!r}). Le scope « {SCOPE_LECTURE} » "
        "est-il devenu un scope par défaut du client de test ? Il doit rester "
        "optionnel."
    )

    code, corps, _ = _appeler(idp, "GET", jeton)
    assert code == 401, (
        f"L'API ACCEPTE un jeton destiné à « {identifiants['AUTRE_API']} » "
        f"(HTTP {code}). C'est la faille que ce lab existe pour fermer : la "
        "signature est bonne, l'émetteur est bon, et le jeton n'est pas pour "
        f"vous. Corps : {corps[:300]}"
    )


def test_un_jeton_sans_le_scope_est_refuse_sur_la_route_qui_l_exige(idp):
    """403 et `insufficient_scope`, pas 401 : le jeton est valide, pas suffisant.

    Vert avant le travail ? Non : l'API de départ ne regarde aucun scope.

    La distinction compte. 401 dit « je ne sais pas qui vous êtes », et un
    client réessaie en s'authentifiant. 403 dit « je sais qui vous êtes, et
    cela ne suffit pas », et réessayer ne servirait à rien.
    """
    jeton = _jeton_utilisateur(idp, f"openid {SCOPE_LECTURE}")

    code, corps, entetes = _appeler(idp, "POST", jeton)
    assert code == 403, (
        f"Une écriture avec un jeton de LECTURE seule rend HTTP {code} au lieu "
        f"de 403. Corps : {corps[:300]}"
    )
    assert "insufficient_scope" in (corps + entetes).lower(), (
        "Le refus ne nomme pas `insufficient_scope`. La RFC 6750 réserve ce "
        "code à ce cas précis, et c'est lui qui dit au client que le problème "
        f"est la permission et non l'identité. Corps : {corps[:200]}"
    )


def test_le_service_de_sauvegarde_lit_mais_n_ecrit_pas(idp):
    """Un accès machine, sans utilisateur, et borné à ce qu'il doit faire.

    Vert avant le travail ? Non : le client n'existe pas.

    Un service de sauvegarde n'a besoin de lire. Lui donner l'écriture parce
    que c'est plus simple est la façon ordinaire de perdre des données, et
    l'octroi par client credentials ne dispense pas de borner les permissions.
    """
    client = _client_declare(idp, SERVICE)

    assert client.get("publicClient") is False, (
        f"Le client « {SERVICE} » est public. Un service qui tourne sur un "
        "serveur peut garder un secret, et doit donc être confidentiel."
    )
    assert client.get("serviceAccountsEnabled") is True, (
        f"Le client « {SERVICE} » n'a pas de compte de service. Sans lui, "
        "l'octroi par client credentials est refusé, et le service n'a aucun "
        "moyen de s'authentifier sans utilisateur."
    )

    jeton = _jeton_du_service(idp)
    revendications = _revendications(jeton)
    accordes = (revendications.get("scope") or "").split()
    assert SCOPE_LECTURE in accordes, (
        f"Le jeton du service ne porte pas « {SCOPE_LECTURE} » "
        f"(scope = {accordes}). Le scope doit lui être attaché PAR DÉFAUT : un "
        "scope optionnel n'arrive que s'il est demandé, et un service n'a "
        "personne pour le demander."
    )
    assert SCOPE_ECRITURE not in accordes, (
        f"Le jeton du service porte « {SCOPE_ECRITURE} » (scope = {accordes}). "
        "Un service de sauvegarde lit, il n'écrit pas."
    )

    code, corps, _ = _appeler(idp, "GET", jeton)
    assert code == 200, (
        f"Le service ne peut pas lire (HTTP {code}). Son jeton porte pourtant "
        f"le scope de lecture. Corps : {corps[:300]}"
    )

    code, corps, _ = _appeler(idp, "POST", jeton)
    assert code == 403, (
        f"Le service peut ÉCRIRE (HTTP {code}). Un accès machine mal borné est "
        f"plus dangereux qu'un accès humain : personne ne le surveille. "
        f"Corps : {corps[:300]}"
    )


def test_le_secret_du_service_ne_traine_dans_aucun_fichier_lisible(idp):
    """Un secret obtenu de l'API d'administration, cherché sur le disque.

    Vert avant le travail ? Non : le client n'existe pas, donc il n'y a pas de
    secret à chercher, et `_client_declare` échoue.

    Le test cherche le secret RÉEL, celui que Keycloak détient, dans les
    fichiers du lab. C'est plus honnête que de chercher des motifs qui
    ressemblent à un secret : il n'y a aucun faux positif possible.
    """
    client = _client_declare(idp, SERVICE)
    secret = _api_admin(idp, f"clients/{client['id']}/client-secret")
    valeur = (secret or {}).get("value", "")
    assert valeur, f"Le client « {SERVICE} » n'a pas de secret."

    # `grep -r` sur les répertoires du lab. Le secret est passé par un fichier
    # pour ne pas apparaître dans la ligne de commande, que `ps` montre à tous.
    res = idp.run(
        f"printf '%s' {valeur!r} > /tmp/motif-test && "
        "grep -rlF -f /tmp/motif-test /opt/iam-lab /opt/socle-iam 2>/dev/null; "
        "rm -f /tmp/motif-test"
    )
    fautifs = [li for li in res.stdout.splitlines() if li.strip()]
    assert not fautifs, (
        "Le secret du service est écrit en clair dans :\n"
        + "\n".join(f"  {f}" for f in fautifs)
        + "\n\nUn secret de client ne s'écrit pas à côté du code. Le service "
        "le reçoit par son environnement, et l'API d'administration reste la "
        "seule source."
    )
