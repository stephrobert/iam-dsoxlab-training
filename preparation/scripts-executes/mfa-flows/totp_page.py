import base64, hashlib, hmac, struct, sys, time

def totp(cle_b32, instant=None, chiffres=6, periode=30):
    cle_b32 = cle_b32.replace(" ", "").upper()
    cle = base64.b32decode(cle_b32 + "=" * (-len(cle_b32) % 8))
    compteur = struct.pack(">Q", int((instant or time.time()) // periode))
    h = hmac.new(cle, compteur, hashlib.sha1).digest()
    o = h[-1] & 0x0F
    return str((struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % 10 ** chiffres).zfill(chiffres)

print(totp(sys.argv[1]))
