import re, glob, html, os
D = "/tmp/claude-1000/-home-bob-Projets-test-astro-5/35a3c76a-c83b-471f-8a4e-cbcb743fffe5/scratchpad/author-production/docs"
for f in glob.glob(D + "/*.html"):
    t = open(f, encoding="utf-8", errors="ignore").read()
    t = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"<(br|/p|/li|/h\d|/div|/tr|/pre)[^>]*>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    open(f[:-5] + ".txt", "w").write(t)
    print(f, len(t))
