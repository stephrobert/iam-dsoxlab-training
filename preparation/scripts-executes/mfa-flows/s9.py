import re, login as L
op=L.ouvrir()
r=L.suivre(op,*L.connexion(op,"alice","phrase-de-passe-longue-2026"))
print(r[0], L.etat(*r), sorted(set(re.findall(r'<input[^>]*name="([^"]+)"',r[2]))))
print(re.findall(r'(Mobile Authenticator Setup)',r[2])[:1], re.findall(r'Unable to scan\?',r[2])[:1])
