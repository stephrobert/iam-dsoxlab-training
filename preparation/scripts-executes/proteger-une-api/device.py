import html, json, re, sys, urllib.parse, urllib.request, http.cookiejar
KC = "http://localhost:8080/realms/lab/protocol/openid-connect"
def post(url, data):
    r = urllib.request.Request(url, urllib.parse.urlencode(data).encode())
    try:
        return json.load(urllib.request.urlopen(r))
    except urllib.error.HTTPError as e:
        return json.load(e)
dev = post(f"{KC}/auth/device", {"client_id": "notes-cli", "scope": "notes:lecture"})
print("user_code", dev["user_code"])
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
page = op.open(dev["verification_uri_complete"]).read().decode()
def form(page):
    m = re.search(r'<form[^>]*action="([^"]+)"', page)
    return html.unescape(m.group(1)), page
act, _ = form(page)
print("step1 form:", re.findall(r'name="(\w+)"', page)[:8])
if "username" in page:
    page = op.open(urllib.request.Request(act, urllib.parse.urlencode({"username": "alice", "password": "Alice-lab-2026"}).encode())).read().decode()
    print("after login:", re.findall(r'name="(\w+)"', page)[:8], re.findall(r'<title>(.*?)</title>', page, re.S))
    # consent page ?
    if "accept" in page:
        act, _ = form(page)
        hidden = dict(re.findall(r'name="(\w+)" value="([^"]*)"', page))
        hidden["accept"] = "Yes"
        page = op.open(urllib.request.Request(act, urllib.parse.urlencode(hidden).encode())).read().decode()
        print("after consent:", re.findall(r'<title>(.*?)</title>', page, re.S), re.sub(r'<[^>]+>', ' ', page)[:0])
tok = post(f"{KC}/token", {"grant_type": "urn:ietf:params:oauth:grant-type:device_code", "client_id": "notes-cli", "device_code": dev["device_code"]})
print({k: (v if k != "access_token" and k != "refresh_token" else "...") for k, v in tok.items()})
open("dev-token.txt", "w").write(tok.get("access_token", ""))
