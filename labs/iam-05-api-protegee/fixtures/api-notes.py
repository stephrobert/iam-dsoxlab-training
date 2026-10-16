"""API témoin « notes ». VERSION DE DÉPART, VOLONTAIREMENT INCOMPLÈTE.

Cette API vérifie la SIGNATURE du jeton, et rien d'autre. Elle fonctionne : un
jeton signé par le fournisseur passe, un jeton bricolé est refusé. C'est
exactement pour cela qu'elle est dangereuse, et c'est le sujet du lab.

Un jeton signé par le même fournisseur mais délivré pour une AUTRE application,
ou sans la permission demandée, est un jeton parfaitement signé. Cette version
l'accepte.

Les quatre contrôles qui manquent, et que le challenge demande d'ajouter :

    issuer      le jeton vient-il du realm attendu, et non d'un autre realm du
                même serveur, dont les clés sont tout aussi valides
    audience    ce jeton est-il destiné À CETTE API, ou à une autre
    expiration  est-il encore valide
    scope       porte-t-il la permission que la route exige

Ne devinez pas où les ajouter : décodez d'abord un jeton et regardez ce qu'il
contient. Le tutoriel montre comment.

Deux routes, deux permissions attendues :

    GET  /notes    lecture
    POST /notes    écriture
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import jwt  # PyJWT

ISSUER = os.environ["ISSUER"]
AUDIENCE = os.environ.get("AUDIENCE", "")
PORT = int(os.environ.get("PORT_API", "8090"))

JWKS = jwt.PyJWKClient(f"{ISSUER}/protocol/openid-connect/certs")

#: La permission que chaque méthode exige. Rien ne la vérifie encore.
SCOPE_PAR_METHODE = {"GET": "notes:lecture", "POST": "notes:ecriture"}


class Gestionnaire(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def repondre(
        self, code: int, corps: dict[str, Any], www_authenticate: str | None = None
    ) -> None:
        charge = json.dumps(corps, ensure_ascii=False).encode()
        self.send_response(code)
        if www_authenticate:
            self.send_header("WWW-Authenticate", www_authenticate)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(charge)))
        self.end_headers()
        self.wfile.write(charge)

    def traiter(self) -> None:
        en_tete = self.headers.get("Authorization", "")
        if not en_tete.startswith("Bearer "):
            return self.repondre(401, {"erreur": "jeton absent"}, "Bearer")

        jeton = en_tete[len("Bearer ") :]
        try:
            cle = JWKS.get_signing_key_from_jwt(jeton)
            # LA SIGNATURE, ET RIEN D'AUTRE.
            #
            # `verify_aud`, `verify_iss` et `verify_exp` sont désactivés, donc
            # PyJWT ne regarde que la cryptographie. Un jeton d'une autre
            # application, d'un autre realm ou périmé passe ici sans un mot.
            revendications = jwt.decode(
                jeton,
                cle.key,
                algorithms=["RS256"],
                options={
                    "verify_aud": False,
                    "verify_iss": False,
                    "verify_exp": False,
                },
            )
        except jwt.PyJWTError as erreur:
            return self.repondre(
                401, {"erreur": str(erreur)}, 'Bearer error="invalid_token"'
            )

        # Le scope attendu est connu, et personne ne le compare.
        attendu = SCOPE_PAR_METHODE.get(self.command, "")

        return self.repondre(
            200,
            {
                "sujet": revendications.get("sub"),
                "scope_attendu": attendu,
                "notes": ["courses", "idées"],
            },
        )

    do_GET = do_POST = traiter

    def log_message(self, format: str, *args: Any) -> None:
        # Sur la sortie d'erreur, et sans l'en-tête Authorization : un journal
        # qui recopie les jetons les rend lisibles à qui lit les journaux.
        import sys

        sys.stderr.write(f"{self.address_string()} {format % args}\n")


if __name__ == "__main__":
    import sys

    sys.stderr.write(f"api notes sur le port {PORT}, issuer {ISSUER}\n")
    HTTPServer(("0.0.0.0", PORT), Gestionnaire).serve_forever()  # noqa: S104
