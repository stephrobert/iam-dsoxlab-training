import sys, jwt
t = sys.argv[1]
k = jwt.PyJWKClient("http://localhost:8080/realms/lab/protocol/openid-connect/certs").get_signing_key_from_jwt(t)
c = jwt.decode(t, k.key, algorithms=["RS256"], options={"verify_aud": False})
print("signature seule : acceptée, aud =", c["aud"])
