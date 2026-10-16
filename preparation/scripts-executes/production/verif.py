"""Verifie un jeton RS256 hors ligne avec une copie locale du JWKS."""
import json
import sys
import time

import jwt

jeton = open(sys.argv[1]).read().strip()
jwks = json.load(open(sys.argv[2]))
entete = jwt.get_unverified_header(jeton)
jwk = next(k for k in jwks["keys"] if k["kid"] == entete["kid"])
cle = jwt.PyJWK(jwk).key
try:
    claims = jwt.decode(jeton, cle, algorithms=["RS256"], issuer=sys.argv[3], options={"verify_aud": False})
    print(f"signature et issuer valides ; exp dans {claims['exp'] - int(time.time())} s")
except jwt.PyJWTError as e:
    print("refuse :", e)
