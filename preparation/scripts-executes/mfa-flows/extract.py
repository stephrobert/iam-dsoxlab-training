import re
t=open('/home/bob/Projets/test-astro-5/.claude/worktrees/formation-iam/src/content/docs/docs/services/identite/keycloak/mfa-flows.mdx').read()
bl=re.findall(r'```bash\n(.*?)```',t,re.S)
print(len(bl))
for i,b in enumerate(bl,1):
    b=b.replace('docker run -d --name keycloak -p 8080:8080','docker run -d --name kc-lab3 -p 8093:8080')
    b=b.replace('curl -sf http://localhost:8080/realms/master','curl -sf http://localhost:8093/realms/master')
    b=b.replace('docker exec keycloak','docker exec kc-lab3').replace('docker rm -f keycloak','docker rm -f kc-lab3')
    open(f'b{i}.sh','w').write(b)
