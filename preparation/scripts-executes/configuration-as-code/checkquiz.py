import json, re
b = "/tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-cac/"
q = json.load(open(b + "quiz-configuration-as-code.json"))["keycloak-configuration-as-code"]
page = open("/home/bob/Projets/test-astro-5/.claude/worktrees/formation-iam/src/content/docs/docs/services/identite/keycloak/configuration-as-code.mdx").read()
heads = set(re.findall(r"^#{2,3} (.+)$", page, re.M))
print(len(q), [x["type"] for x in q])
for i, x in enumerate(q, 1):
    assert x["section"] in heads, x["section"]
    assert len(x["explication"]) >= 120 and x["explication"].count("**") >= 2
    if x["type"] == "qcm":
        L = sorted(len(c) for c in x["choix"])
        assert x["reponse"] in x["choix"]
        print(i, "rang", L.index(len(x["reponse"])) + 1, [len(c) for c in x["choix"]], len(x["reponse"]))
print("ok")
