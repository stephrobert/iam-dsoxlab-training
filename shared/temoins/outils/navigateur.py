"""Rejoue une connexion navigateur contre Keycloak, bibliothèque standard seule.

Cet outil sert aux TESTS, pas à l'apprenant. Il existe parce qu'un flux de code
d'autorisation ne se vérifie pas par une requête : il faut suivre les
redirections, tenir les cookies de session, poster le formulaire de connexion,
et récupérer le code sur l'URI de redirection. Un test qui se contenterait
d'appeler le point d'autorisation mesurerait qu'une page s'affiche, ce qui est
vrai même pour un client mal configuré.

Repris de `preparation/scripts-executes/mfa-flows/login.py`, réellement joué le
2026-10-15 contre Keycloak 26.7.0, et généralisé : le realm, le client, l'URI
de redirection et PKCE sont des paramètres, là où le script d'origine les avait
en dur.

Aucune dépendance : il tourne avec le `python3` de la machine, sans
environnement virtuel. C'est voulu, les tests ne doivent pas dépendre d'une
installation qu'un lab pourrait défaire.

Usage, depuis la machine du lab :

    python3 navigateur.py --realm formation --client appli-notes \
        --redirect-uri http://localhost:9080/callback \
        --utilisateur alice --mot-de-passe '...' --pkce

Il écrit un objet JSON sur la sortie standard et sort en 0 même sur un refus :
c'est au test de juger. Un échec de l'outil lui-même sort en 2, pour qu'un test
ne confonde jamais « Keycloak a refusé » avec « l'outil n'a pas pu mesurer ».
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import http.cookiejar
import json
import re
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request

ERREUR_OUTIL = 2


class SansRedirection(urllib.request.HTTPRedirectHandler):
    """Ne suit aucune redirection : c'est l'outil qui décide de les suivre.

    Le suivi automatique perdrait l'URI de redirection finale, qui porte le code
    d'autorisation, et la perdrait en silence.
    """

    def redirect_request(self, *args, **kwargs):
        return None


def ouvrir_navigateur() -> urllib.request.OpenerDirector:
    politique = http.cookiejar.DefaultCookiePolicy(secure_protocols=("http", "https"))
    bocal = http.cookiejar.CookieJar(politique)
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(bocal), SansRedirection
    )


def appeler(
    navigateur: urllib.request.OpenerDirector,
    url: str,
    donnees: dict[str, str] | None = None,
) -> tuple[int, str | None, str]:
    corps = urllib.parse.urlencode(donnees).encode() if donnees else None
    # URL bâtie depuis le realm et le client passés en option, jamais
    # depuis une entrée : le schéma est toujours http ou https.
    requete = urllib.request.Request(url, data=corps)  # noqa: S310
    try:
        reponse = navigateur.open(requete)
        return reponse.status, reponse.headers.get("Location"), reponse.read().decode()
    except urllib.error.HTTPError as erreur:
        return erreur.code, erreur.headers.get("Location"), erreur.read().decode()


def titre_de_page(page: str) -> str:
    trouve = re.search(r'id="kc-page-title"[^>]*>\s*(.*?)\s*<', page, re.S)
    return html.unescape(trouve.group(1)) if trouve else "(sans titre)"


def message_d_erreur(page: str) -> str:
    """Le message que Keycloak affiche, quand il refuse en rendant une page.

    Un refus de configuration (URI de redirection invalide, client inconnu) ne
    rend pas un code HTTP d'erreur : il rend une page 200 qui porte le message.
    Un test qui ne regarderait que le code HTTP conclurait au succès.
    """
    for motif in (
        r'id="kc-error-message"[^>]*>\s*<p[^>]*>\s*(.*?)\s*</p>',
        r'class="[^"]*kc-feedback-text[^"]*"[^>]*>\s*(.*?)\s*<',
    ):
        trouve = re.search(motif, page, re.S)
        if trouve:
            return html.unescape(re.sub(r"<[^>]+>", "", trouve.group(1))).strip()
    return ""


def formulaire(page: str) -> tuple[str, dict[str, str]]:
    trouve = re.search(r'<form[^>]*action="([^"]+)"', page)
    if not trouve:
        raise RuntimeError(
            "La page rendue ne porte aucun formulaire. Keycloak a probablement "
            f"refusé la requête. Titre de la page : « {titre_de_page(page)} », "
            f"message : « {message_d_erreur(page)} »"
        )
    action = html.unescape(trouve.group(1))
    caches = {
        nom: html.unescape(valeur)
        for nom, valeur in re.findall(
            r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', page
        )
    }
    return action, caches


def verificateur_pkce() -> tuple[str, str]:
    """Un couple (verifier, challenge) en S256, selon la RFC 7636."""
    verifieur = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    condensat = hashlib.sha256(verifieur.encode("ascii")).digest()
    defi = base64.urlsafe_b64encode(condensat).rstrip(b"=").decode()
    return verifieur, defi


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--base", default="http://127.0.0.1:8080")
    analyseur.add_argument("--realm", required=True)
    analyseur.add_argument("--client", required=True)
    analyseur.add_argument("--redirect-uri", required=True)
    analyseur.add_argument("--utilisateur", required=True)
    analyseur.add_argument("--mot-de-passe", required=True)
    analyseur.add_argument("--scope", default="openid")
    analyseur.add_argument("--pkce", action="store_true",
                           help="ajoute code_challenge en S256")
    analyseur.add_argument("--sans-verifier", action="store_true",
                           help="échange le code SANS code_verifier : sert à "
                                "prouver qu'un client qui exige PKCE refuse")
    analyseur.add_argument("--nonce", default=None,
                           help="nonce imposé, pour vérifier qu'il est repris "
                                "dans l'ID token")
    args = analyseur.parse_args()

    resultat: dict[str, object] = {"etapes": []}
    navigateur = ouvrir_navigateur()

    nonce = args.nonce or secrets.token_urlsafe(16)
    parametres = {
        "client_id": args.client,
        "response_type": "code",
        "scope": args.scope,
        "redirect_uri": args.redirect_uri,
        "state": secrets.token_urlsafe(12),
        "nonce": nonce,
    }
    verifieur = None
    if args.pkce:
        verifieur, defi = verificateur_pkce()
        parametres["code_challenge"] = defi
        parametres["code_challenge_method"] = "S256"

    autorisation = (
        f"{args.base}/realms/{args.realm}/protocol/openid-connect/auth"
        f"?{urllib.parse.urlencode(parametres)}"
    )

    try:
        code_http, lieu, page = appeler(navigateur, autorisation)
        resultat["etapes"].append({"etape": "autorisation", "http": code_http})

        # Keycloak peut rediriger vers la page de connexion avant de la servir.
        tours = 0
        while code_http in (301, 302, 303) and lieu and not lieu.startswith(
            args.redirect_uri
        ):
            tours += 1
            if tours > 10:
                raise RuntimeError("plus de dix redirections : boucle probable")
            code_http, lieu, page = appeler(navigateur, lieu)

        # Un refus de configuration arrive ici, en page 200 qui porte un message.
        if code_http not in (301, 302, 303):
            message = message_d_erreur(page)
            if message:
                resultat["refus_a_l_autorisation"] = message
                resultat["titre"] = titre_de_page(page)
                print(json.dumps(resultat, ensure_ascii=False))
                return 0

            action, _ = formulaire(page)
            code_http, lieu, page = appeler(
                navigateur,
                action,
                {"username": args.utilisateur, "password": args.mot_de_passe,
                 "credentialId": ""},
            )
            resultat["etapes"].append({"etape": "connexion", "http": code_http})

        tours = 0
        while code_http in (301, 302, 303) and lieu and not lieu.startswith(
            args.redirect_uri
        ):
            tours += 1
            if tours > 10:
                raise RuntimeError("plus de dix redirections après la connexion")
            code_http, lieu, page = appeler(navigateur, lieu)

        if not (lieu and lieu.startswith(args.redirect_uri)):
            resultat["connexion_refusee"] = True
            resultat["titre"] = titre_de_page(page)
            resultat["message"] = message_d_erreur(page)
            print(json.dumps(resultat, ensure_ascii=False))
            return 0

        retour = urllib.parse.parse_qs(urllib.parse.urlparse(lieu).query)
        resultat["redirection"] = lieu.split("?")[0]
        if "code" not in retour:
            resultat["pas_de_code"] = retour
            print(json.dumps(resultat, ensure_ascii=False))
            return 0
        resultat["code_obtenu"] = True
        resultat["nonce_envoye"] = nonce

        echange = {
            "grant_type": "authorization_code",
            "client_id": args.client,
            "code": retour["code"][0],
            "redirect_uri": args.redirect_uri,
        }
        if verifieur and not args.sans_verifier:
            echange["code_verifier"] = verifieur

        code_http, _, corps = appeler(
            navigateur,
            f"{args.base}/realms/{args.realm}/protocol/openid-connect/token",
            echange,
        )
        resultat["echange_http"] = code_http
        try:
            resultat["jetons"] = json.loads(corps)
        except json.JSONDecodeError:
            resultat["echange_corps"] = corps[:400]

    except RuntimeError as erreur:
        print(json.dumps({"erreur_outil": str(erreur)}, ensure_ascii=False),
              file=sys.stderr)
        return ERREUR_OUTIL
    except urllib.error.URLError as erreur:
        print(json.dumps({"erreur_outil": f"injoignable : {erreur}"},
                         ensure_ascii=False), file=sys.stderr)
        return ERREUR_OUTIL

    print(json.dumps(resultat, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
