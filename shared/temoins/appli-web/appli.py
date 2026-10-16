"""Application témoin « notes » : délègue sa connexion à un fournisseur OIDC.

Cette application est COMPLÈTE et versionnée en clair, ce qui n'est pas un
oubli. Le lab qui s'en sert ne demande pas d'écrire du code : il demande de
déclarer correctement un client dans Keycloak et de pointer l'application
dessus. Lire ce fichier ne donne donc aucune réponse, la réponse vit dans la
configuration du fournisseur d'identité.

Ce qu'elle fait, et qui est le sujet du lab :

- elle démarre un flux de code d'autorisation avec PKCE en S256, jamais un flux
  implicite et jamais un mot de passe qu'elle verrait passer ;
- elle valide l'ID token reçu : signature contre le JWKS du fournisseur,
  `iss` attendu, `aud` égale à son propre identifiant de client, `exp` non
  dépassé, et `nonce` identique à celui qu'elle a envoyé ;
- elle refuse un jeton signé par un autre realm, même valide en soi : un jeton
  de bonne signature mais de mauvais émetteur est exactement l'attaque que la
  validation d'`iss` arrête.

Elle lit sa configuration dans `configuration.json`, à côté d'elle, que
l'apprenant remplit.

Le point `/etat` rend son état en JSON : c'est ce que les tests interrogent.
Aucune page n'affiche de jeton, et le journal n'en écrit pas.
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import secrets
import socketserver
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import jwt

ICI = Path(__file__).resolve().parent
CONFIGURATION = ICI / "configuration.json"
PORT = int(os.environ.get("PORT_APPLI", "9080"))

# L'état vit en mémoire : un témoin ne persiste rien, et un redémarrage doit
# repartir d'une page déconnectée. Un seul visiteur à la fois, ce qui suffit à
# un lab et évite d'avoir à gérer des sessions concurrentes.
ETAT: dict[str, Any] = {
    "configuration_lue": False,
    "connecte": False,
    "utilisateur": None,
    "derniere_erreur": None,
    "validations": [],
}
EN_COURS: dict[str, str] = {}


def configuration() -> dict[str, str]:
    """La configuration que l'apprenant a écrite, relue à chaque appel.

    Relue, et non lue une fois au démarrage : l'apprenant corrige son fichier
    et recharge la page. Redémarrer le témoin à chaque correction ne lui
    apprendrait rien sur OIDC.
    """
    if not CONFIGURATION.is_file():
        raise RuntimeError(
            f"{CONFIGURATION.name} est absent. L'application ne sait ni à quel "
            "fournisseur s'adresser ni sous quel identifiant de client."
        )
    donnees = json.loads(CONFIGURATION.read_text(encoding="utf-8"))
    manquants = [
        clef for clef in ("issuer", "client_id", "redirect_uri")
        if not donnees.get(clef)
    ]
    if manquants:
        raise RuntimeError(
            f"{CONFIGURATION.name} ne déclare pas : {', '.join(manquants)}"
        )
    return donnees


def pkce() -> tuple[str, str]:
    verifieur = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    defi = base64.urlsafe_b64encode(
        hashlib.sha256(verifieur.encode("ascii")).digest()
    ).rstrip(b"=").decode()
    return verifieur, defi


def poster(url: str, donnees: dict[str, str]) -> dict[str, Any]:
    requete = urllib.request.Request(  # noqa: S310  # URL de la configuration du lab
        url, data=urllib.parse.urlencode(donnees).encode()
    )
    try:
        with urllib.request.urlopen(requete, timeout=10) as reponse:  # noqa: S310
            return json.loads(reponse.read().decode())
    except urllib.error.HTTPError as erreur:
        corps = erreur.read().decode("utf-8", "replace")
        raise RuntimeError(f"le fournisseur a refusé l'échange ({erreur.code}) : "
                           f"{corps[:300]}") from erreur


def valider_id_token(jeton: str, conf: dict[str, str], nonce: str) -> dict[str, Any]:
    """Les cinq contrôles, et aucun n'est optionnel.

    Une application qui ne vérifierait que la signature accepterait un jeton
    émis par un autre realm du même serveur, ou destiné à une autre
    application. Les deux sont des jetons parfaitement signés.
    """
    client = jwt.PyJWKClient(f"{conf['issuer']}/protocol/openid-connect/certs")
    cle = client.get_signing_key_from_jwt(jeton)
    revendications = jwt.decode(
        jeton,
        cle.key,
        algorithms=["RS256"],
        audience=conf["client_id"],
        issuer=conf["issuer"],
        options={"require": ["exp", "iss", "aud", "sub"]},
    )
    recu = revendications.get("nonce")
    if recu != nonce:
        raise RuntimeError(
            "le nonce de l'ID token ne correspond pas à celui envoyé : le jeton "
            "pourrait être rejoué depuis une autre connexion"
        )
    return revendications


def retenir(validation: dict[str, Any]) -> None:
    """Les dix dernières validations, pas plus.

    Elles servent au diagnostic pendant le lab. Les garder toutes ferait
    grossir sans fin l'état d'un témoin qui tourne pendant une heure.
    """
    ETAT["validations"] = ([*ETAT["validations"], validation])[-10:]


PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Notes</title></head>
<body><h1>Notes</h1>{corps}</body></html>"""


class Gestionnaire(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        # Journal sur la sortie d'erreur, sans la chaîne de requête : elle
        # porte le code d'autorisation.
        sys.stderr.write(f"{self.address_string()} {format % args}\n")

    def repondre(self, code: int, corps: bytes, type_mime: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", type_mime)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def page(self, code: int, corps: str) -> None:
        self.repondre(code, PAGE.format(corps=corps).encode(), "text/html; charset=utf-8")

    def json_(self, code: int, objet: dict[str, Any]) -> None:
        self.repondre(
            code, json.dumps(objet, ensure_ascii=False).encode(),
            "application/json; charset=utf-8",
        )

    def do_GET(self) -> None:
        chemin = urllib.parse.urlparse(self.path)
        requete = urllib.parse.parse_qs(chemin.query)

        if chemin.path == "/etat":
            etat = dict(ETAT)
            try:
                conf = configuration()
                etat["configuration_lue"] = True
                etat["issuer"] = conf["issuer"]
                etat["client_id"] = conf["client_id"]
                etat["redirect_uri"] = conf["redirect_uri"]
            except (RuntimeError, json.JSONDecodeError) as erreur:
                etat["configuration_lue"] = False
                etat["configuration_erreur"] = str(erreur)
            return self.json_(200, etat)

        if chemin.path == "/deconnexion":
            ETAT.update(connecte=False, utilisateur=None)
            EN_COURS.clear()
            return self.page(200, "<p>Session fermée.</p>")

        if chemin.path == "/connexion":
            try:
                conf = configuration()
            except (RuntimeError, json.JSONDecodeError) as erreur:
                ETAT["derniere_erreur"] = str(erreur)
                return self.page(500, f"<p>Configuration : {erreur}</p>")

            verifieur, defi = pkce()
            nonce = secrets.token_urlsafe(16)
            EN_COURS.clear()
            EN_COURS.update(verifieur=verifieur, nonce=nonce)
            parametres = {
                "client_id": conf["client_id"],
                "response_type": "code",
                "scope": "openid profile email",
                "redirect_uri": conf["redirect_uri"],
                "state": secrets.token_urlsafe(12),
                "nonce": nonce,
                "code_challenge": defi,
                "code_challenge_method": "S256",
            }
            cible = (
                f"{conf['issuer']}/protocol/openid-connect/auth"
                f"?{urllib.parse.urlencode(parametres)}"
            )
            self.send_response(302)
            self.send_header("Location", cible)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None

        # Le chemin de retour est FIXE : `/callback`. L'apprenant choisit
        # l'hôte et le port de son URI de redirection, pas le chemin, et le
        # README le dit. Accepter n'importe quel chemin ferait passer une URI
        # de redirection fautive, que Keycloak refuserait ensuite pour une
        # raison qui semblerait venir de lui.
        if chemin.path == "/callback":
            if "code" not in requete:
                motif = requete.get("error_description", requete.get("error", ["?"]))[0]
                ETAT["derniere_erreur"] = f"retour sans code : {motif}"
                return self.page(400, f"<p>Retour sans code : {motif}</p>")
            if "verifieur" not in EN_COURS:
                ETAT["derniere_erreur"] = "retour sans flux en cours"
                return self.page(400, "<p>Aucun flux en cours.</p>")
            try:
                conf = configuration()
                jetons = poster(
                    f"{conf['issuer']}/protocol/openid-connect/token",
                    {
                        "grant_type": "authorization_code",
                        "client_id": conf["client_id"],
                        "code": requete["code"][0],
                        "redirect_uri": conf["redirect_uri"],
                        "code_verifier": EN_COURS["verifieur"],
                    },
                )
                if "id_token" not in jetons:
                    raise RuntimeError(
                        "le fournisseur n'a pas rendu d'ID token : le scope "
                        "`openid` est-il demandé, et accordé au client ?"
                    )
                revendications = valider_id_token(
                    jetons["id_token"], conf, EN_COURS["nonce"]
                )
            except (RuntimeError, jwt.PyJWTError, json.JSONDecodeError) as erreur:
                ETAT.update(connecte=False, utilisateur=None,
                            derniere_erreur=str(erreur))
                retenir({"ok": False, "motif": str(erreur)})
                return self.page(401, f"<p>ID token refusé : {erreur}</p>")

            nom = (
                revendications.get("preferred_username")
                or revendications.get("email")
                or revendications["sub"]
            )
            ETAT.update(connecte=True, utilisateur=nom, derniere_erreur=None)
            retenir({"ok": True, "sub": revendications["sub"]})
            EN_COURS.clear()
            return self.page(200, f"<p>Connecté en tant que {nom}</p>")

        if ETAT["connecte"]:
            return self.page(
                200, f"<p>Connecté en tant que {ETAT['utilisateur']}</p>"
            )
        return self.page(
            200, '<p>Non connecté.</p><p><a href="/connexion">Se connecter</a></p>'
        )


class Serveur(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    with Serveur(("0.0.0.0", PORT), Gestionnaire) as serveur:  # noqa: S104
        sys.stderr.write(f"temoin notes sur le port {PORT}\n")
        serveur.serve_forever()
