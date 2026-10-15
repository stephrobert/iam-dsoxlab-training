"""API témoin « notes » : valide les jetons Keycloak en local."""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import jwt  # PyJWT

# Simulation d'une horloge décalée : HORLOGE_DECALAGE en secondes (test seulement)
DECALAGE = int(os.environ.get("HORLOGE_DECALAGE", "0"))
if DECALAGE:
    import datetime as _dt
    import jwt.api_jwt as _api

    class _Horloge(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return super().now(tz) + _dt.timedelta(seconds=DECALAGE)

    _api.datetime = _Horloge

ISSUER = os.environ["ISSUER"]
AUDIENCE = os.environ["AUDIENCE"]
JWKS = jwt.PyJWKClient(f"{ISSUER}/protocol/openid-connect/certs")
SCOPE_PAR_ROUTE = {"GET": "notes:lecture", "POST": "notes:ecriture"}


class Handler(BaseHTTPRequestHandler):
    def repondre(self, code, corps, www_authenticate=None):
        self.send_response(code)
        if www_authenticate:
            self.send_header("WWW-Authenticate", www_authenticate)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(corps).encode())

    def traiter(self):
        scope_requis = SCOPE_PAR_ROUTE[self.command]
        en_tete = self.headers.get("Authorization", "")
        if not en_tete.startswith("Bearer "):
            return self.repondre(401, {"erreur": "jeton absent"}, "Bearer")
        jeton = en_tete[len("Bearer "):]
        try:
            cle = JWKS.get_signing_key_from_jwt(jeton)
            claims = jwt.decode(
                jeton, cle.key, algorithms=["RS256"],
                audience=AUDIENCE, issuer=ISSUER,
                options={"require": ["exp", "iss", "aud"]},
            )
        except jwt.PyJWTError as exc:
            return self.repondre(
                401, {"erreur": str(exc)}, 'Bearer error="invalid_token"')
        if scope_requis not in claims.get("scope", "").split():
            return self.repondre(
                403, {"erreur": "scope manquant"},
                f'Bearer error="insufficient_scope", scope="{scope_requis}"')
        self.repondre(200, {"sub": claims["sub"], "notes": ["courses", "idées"]})

    do_GET = do_POST = traiter


HTTPServer(("127.0.0.1", 8090), Handler).serve_forever()
