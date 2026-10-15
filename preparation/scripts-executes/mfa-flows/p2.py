import re, html, login as L
MDP="phrase-de-passe-longue-2026"
for u in ("alice","bruno"):
    op=L.ouvrir()
    r=L.suivre(op,*L.connexion(op,u,MDP))
    print(u, r[0], L.etat(*r))
    if True:
        for m in re.findall(r'(?:alert|message|error)[^>]*>\s*(?:<[^>]+>\s*)*([^<]{3,120})', r[2]):
            print("  msg:", html.unescape(m.strip()))
        open(f"p2_{u}.html","w").write(r[2])
