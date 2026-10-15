"""TOTP RFC 6238 (SHA-1, 6 chiffres, 30 s) avec la seule bibliothèque standard."""
import base64, hashlib, hmac, struct, sys, time

def totp(secret_b32: str, at: float | None = None, digits: int = 6, period: int = 30) -> str:
    cle = base64.b32decode(secret_b32.replace(" ", "").upper() + "=" * (-len(secret_b32.replace(" ", "")) % 8))
    compteur = struct.pack(">Q", int((time.time() if at is None else at) // period))
    h = hmac.new(cle, compteur, hashlib.sha1).digest()
    o = h[-1] & 0x0F
    return str((struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % 10 ** digits).zfill(digits)

if __name__ == "__main__":
    print(totp(sys.argv[1]))
