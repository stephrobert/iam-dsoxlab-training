"""Rejoue une connexion navigateur avec la seule bibliothèque standard."""
import html, http.cookiejar, re, sys, urllib.parse, urllib.request
import totp as t

BASE = "http://127.0.0.1:8093/realms/lab/protocol/openid-connect/auth"
PARAMS = {"client_id": "appli-test", "response_type": "code", "scope": "openid",
          "redirect_uri": "http://localhost:9999/cb"}

class PasDeSuivi(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None

def ouvrir():
    jar = http.cookiejar.CookieJar(http.cookiejar.DefaultCookiePolicy(secure_protocols=("http", "https")))
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), PasDeSuivi)

def appel(op, url, data=None):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None)
    try:
        r = op.open(req)
        return r.status, r.headers.get("Location"), r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location"), e.read().decode()

def titre(page):
    m = re.search(r'id="kc-page-title"[^>]*>\s*(.*?)\s*<', page, re.S)
    return html.unescape(m.group(1)) if m else "(sans titre)"

def formulaire(page):
    action = html.unescape(re.search(r'<form[^>]*action="([^"]+)"', page).group(1))
    champs = {n: html.unescape(v) for n, v in re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', page)}
    return action, champs

def etat(code, loc, page):
    if code in (301, 302, 303) and loc and loc.startswith("http://localhost:9999"):
        return "REDIRIGE vers l'application avec un code d'autorisation" if "code=" in loc else "REDIRIGE " + loc[:60]
    if code in (301, 302, 303):
        return "redirection interne"
    return "PAGE : " + titre(page)

def connexion(op, user, mdp):
    code, loc, page = appel(op, BASE + "?" + urllib.parse.urlencode(PARAMS))
    action, _ = formulaire(page)
    return appel(op, action, {"username": user, "password": mdp, "credentialId": ""})

def suivre(op, code, loc, page):
    while code in (301, 302, 303) and loc and not loc.startswith("http://localhost:9999"):
        code, loc, page = appel(op, loc)
    return code, loc, page
