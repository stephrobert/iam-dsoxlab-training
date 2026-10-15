import html, re, time, login as L, totp as T
MDP = "phrase-de-passe-longue-2026"

def champs(page):
    return re.findall(r'<input[^>]*name="([^"]+)"', page)

# 1. première connexion d'alice : enrôlement forcé
op = L.ouvrir()
r = L.suivre(op, *L.connexion(op, "alice", MDP))
print("1. mot de passe seul        :", L.etat(*r).replace("PAGE : ", "page : "), "| champs :", sorted(set(champs(r[2])) - {"authenticationExecution"}))
lien = html.unescape(re.search(r'<a[^>]*href="([^"]*mode=manual[^"]*)"', r[2]).group(1))
manuel = L.appel(op, lien)
action, cach = L.formulaire(manuel[2])
brut = cach["totpSecret"]
clef = re.search(r'id="kc-totp-secret-key"[^>]*>\s*([A-Z2-7 ]+?)\s*<', manuel[2]).group(1)
secret = clef.replace(" ", "")
print("   clé manuelle affichée     :", len(secret), "caractères base32")
code = T.totp(secret)
r2 = L.suivre(op, *L.appel(op, action, {"totp": code, "totpSecret": brut, "userLabel": "telephone-alice", "saveTOTPBtn": ""}))
print("   enrôlement avec un code  :", L.etat(*r2))

# 2. seconde connexion : le code est exigé
op = L.ouvrir()
r = L.suivre(op, *L.connexion(op, "alice", MDP))
print("2. mot de passe seul        :", L.etat(*r), "| champs :", sorted(set(champs(r[2])) - {"authenticationExecution"}))
action, _ = L.formulaire(r[2])
fauxcode = "000000" if T.totp(secret) != "000000" else "111111"
rr = L.appel(op, action, {"otp": fauxcode, "login": "Sign In"})
print("   code faux                :", L.etat(*rr), re.findall(r'(Invalid authenticator code\.?)', rr[2])[:1])
action, _ = L.formulaire(rr[2])
rr = L.suivre(op, *L.appel(op, action, {"otp": T.totp(secret, time.time() + 30), "login": "Sign In"}))
print("   code correct             :", L.etat(*rr))
# 3. rejeu du même code dans une nouvelle session
op = L.ouvrir()
r = L.suivre(op, *L.connexion(op, "alice", MDP))
action, _ = L.formulaire(r[2])
rr = L.appel(op, action, {"otp": T.totp(secret, time.time() + 30), "login": "Sign In"})
print("3. même code, 2e session    :", L.etat(*rr), re.findall(r'(Invalid authenticator code\.?)', rr[2])[:1])
# 4. bruno reste sans second facteur
op = L.ouvrir()
print("4. bruno                    :", L.etat(*L.suivre(op, *L.connexion(op, "bruno", MDP))))
open("secret_alice.txt","w").write(secret)
