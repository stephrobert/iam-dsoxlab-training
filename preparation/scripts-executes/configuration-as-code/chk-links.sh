#!/usr/bin/env bash
R=/home/bob/Projets/test-astro-5/.claude/worktrees/formation-iam/src/content/docs
for u in \
 /docs/services/identite/keycloak/installation/ \
 /docs/services/identite/keycloak/administration/ \
 /docs/infra-as-code/provisionnement/terraform/decouvrir/installer-terraform/ \
 /docs/infra-as-code/provisionnement/terraform/decouvrir/workflow-terraform/ \
 /docs/infra-as-code/fondamentaux/etat-plan-reconciliation/ \
 /docs/services/identite/keycloak/kubernetes/ \
 /docs/infra-as-code/fondamentaux/idempotence-convergence-derive/ \
 /docs/infra-as-code/fondamentaux/traiter-derive/ \
 /docs/infra-as-code/fondamentaux/secrets/ \
 /docs/infra-as-code/provisionnement/terraform/state/backends-terraform/ \
 /docs/services/identite/keycloak/depanner-integration/ \
 /docs/infra-as-code/provisionnement/terraform/state/diagnostiquer-state/ \
 /docs/infra-as-code/fondamentaux/reprendre-existant/ ; do
  p="$R$u"; p="${p%/}"
  f=""
  for c in "$p.mdx" "$p.md" "$p/index.mdx" "$p/index.md"; do [ -f "$c" ] && f="$c" && break; done
  if [ -z "$f" ]; then echo "MISSING $u"; else echo "OK $u draft=$(grep -m1 -E '^draft:' "$f" || echo none)"; fi
done
ls /home/bob/Projets/test-astro-5/.claude/worktrees/formation-iam/src/schemas/ 2>/dev/null | head -3
find /home/bob/Projets/test-astro-5/.claude/worktrees/formation-iam/src/schemas -name 'realm-as-code*'
K=/home/bob/Projets/test-astro-5/.claude/worktrees/formation-iam/src/content/docs/docs/services/identite/keycloak
grep -n -i -E 'terraform|partial-export|keycloak-config-cli|RealmImport|kcadm' $K/administration.mdx $K/kubernetes.mdx $K/depanner-integration.mdx | cut -c1-260
