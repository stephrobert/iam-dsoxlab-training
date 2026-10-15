import datetime as dt, sys, jwt, jwt.api_jwt as api
class H(dt.datetime):
    @classmethod
    def now(cls, tz=None): return super().now(tz) + dt.timedelta(seconds=-30)
api.datetime = H
t = sys.argv[1]
k = jwt.PyJWKClient("http://localhost:8080/realms/lab/protocol/openid-connect/certs").get_signing_key_from_jwt(t)
for lw in (0, 60):
    try:
        jwt.decode(t, k.key, algorithms=["RS256"], audience="notes-api", leeway=lw); print("leeway", lw, ": accepté")
    except jwt.PyJWTError as e: print("leeway", lw, ":", e)
