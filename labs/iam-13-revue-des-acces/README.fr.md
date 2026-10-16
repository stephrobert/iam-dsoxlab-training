# Tutoriel : un drapeau qui ment, et une API qui répond en YAML

Ce tutoriel ne fait pas le challenge. Il vous montre trois choses qui coûtent
une après-midi chacune, mesurées sur cette machine le 2026-10-16, sur votre
propre realm, avant que vous ne touchiez à rien.

```bash
KC=http://127.0.0.1:8080
IDS=/opt/iam-lab/identifiants-lab.txt
REALM=$(grep '^REALM=' $IDS | cut -d= -f2-)
SCIM=$(grep '^URL_SCIM=' $IDS | cut -d= -f2-)
U=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME=' /opt/socle-iam/.env | cut -d= -f2-)
P=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD=' /opt/socle-iam/.env | cut -d= -f2-)
ADM=$(curl -s -X POST "$KC/realms/master/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  -d "username=$U" -d "password=$P" | jq -r .access_token)
echo "realm $REALM, API SCIM attendue sur $SCIM"
```

Notez le `-f2-`, et non `-f2`. Ces valeurs contiennent des URL, et une URL ne
contient pas de `=` mais elle contient des `:` et des `/` ; dans un autre lab,
un DN a coûté une heure à cette différence exacte. `-f2` couperait au premier
`=` et vous rendrait un fragment.

## 1. Le serveur dit la fonctionnalité activée, et l'API répond 404

Regardez ce que le serveur annonce, puis ce qu'il sert :

```bash
curl -s "$KC/admin/realms/$REALM" -H "Authorization: Bearer $ADM" \
  | jq '{scimApiEnabled, attributs_scim: (.attributes | with_entries(
      select(.key | test("scim"; "i"))))}'

curl -s -o /dev/null -w 'ServiceProviderConfig : HTTP %{http_code}\n' \
  "$SCIM/ServiceProviderConfig"
```

`404`. La fonctionnalité est active au niveau du serveur et fermée sur ce realm,
et le drapeau qui l'ouvre est `scimApiEnabled`, à la **racine** de la
représentation du realm.

Vient maintenant ce qui coûte l'après-midi. Mettez-le dans les `attributes` du
realm, là où va d'habitude la configuration, et observez :

```bash
curl -s "$KC/admin/realms/$REALM" -H "Authorization: Bearer $ADM" \
  | jq '.attributes.scimApiEnabled = "true"' > /tmp/realm-essai.json
curl -s -o /dev/null -w 'PUT dans attributes : HTTP %{http_code}\n' -X PUT \
  "$KC/admin/realms/$REALM" -H "Authorization: Bearer $ADM" \
  -H 'Content-Type: application/json' -d @/tmp/realm-essai.json

curl -s "$KC/admin/realms/$REALM" -H "Authorization: Bearer $ADM" \
  | jq '.scimApiEnabled'
curl -s -o /dev/null -w 'et l API  : HTTP %{http_code}\n' \
  "$SCIM/ServiceProviderConfig"
```

`HTTP 204`, et la valeur se relit à `false`. La mise à jour a réussi et n'a rien
changé. Rien dans la réponse, rien dans les journaux, rien dans la console ne
dit que la clef est partie dans un endroit qui n'est jamais lu.

C'est la forme à reconnaître, bien au-delà de ce seul drapeau : **une mise à
jour qui rend un code de succès n'est pas un état qui a changé.** Relisez
l'état.

À la racine, cela marche :

```bash
curl -s "$KC/admin/realms/$REALM" -H "Authorization: Bearer $ADM" \
  | jq '.scimApiEnabled = true' > /tmp/realm-essai.json
curl -s -o /dev/null -w 'PUT a la racine : HTTP %{http_code}\n' -X PUT \
  "$KC/admin/realms/$REALM" -H "Authorization: Bearer $ADM" \
  -H 'Content-Type: application/json' -d @/tmp/realm-essai.json

curl -s "$KC/admin/realms/$REALM" -H "Authorization: Bearer $ADM" \
  | jq '.scimApiEnabled'
curl -s -o /dev/null -w 'et l API  : HTTP %{http_code}\n' \
  "$SCIM/ServiceProviderConfig"
```

`401` au lieu de `404`. C'est la mesure qui compte : l'API existe désormais et
elle demande qui vous êtes. Gardez cette distinction, elle vous servira dans le
challenge, et laissez le realm tel que vous le trouvez maintenant ou refermez-le,
comme vous préférez : le setup le referme à chaque `dsoxlab run`.

## 2. Deux 401, deux raisons différentes, les deux en forme SCIM

Essayez le jeton que vous avez, celui de l'administrateur du realm `master` :

```bash
curl -s "$SCIM/ServiceProviderConfig" -H "Authorization: Bearer $ADM" | jq .
```

« Bearer token required ». Votre jeton est parfaitement valide et parfaitement
administratif, et c'est le mauvais jeton : cette API est servie **par le
realm**, et elle veut un jeton **de ce realm**.

Un client de ce realm, en client credentials, donne donc un jeton du bon realm.
Celui-là obtient un autre message, « Invalid token audience », et la différence
est toute la leçon. Le premier 401 dit « je ne vous connais pas ». Le second dit
« je vous connais, et ce jeton n'a pas été émis pour moi ».

Une audience n'est pas un droit. C'est le nom du destinataire, écrit dans le
jeton, et l'API vérifie que c'est son propre nom. Vous avez donné une audience à
un jeton au lab 05, avec un mappeur d'audience ; la seule question ici est
**quel** nom elle veut. Quatre candidats sont plausibles, un seul marche. L'URL
du ServiceProvider que vous avez déjà dans `$SCIM` est un point de départ
raisonnable.

## 3. L'API des workflows répond en YAML

L'API de cycle de vie est celle qui désactivera les comptes inactifs sans que
personne soit là. Demandez-lui ce qu'elle veut :

```bash
curl -s "$KC/admin/realms/$REALM/workflows" -H "Authorization: Bearer $ADM"
curl -s "$KC/admin/realms/$REALM/workflows" -H "Authorization: Bearer $ADM" \
  | jq . 2>&1 | head -2

echo "== POST vide =="
curl -s -X POST "$KC/admin/realms/$REALM/workflows" \
  -H "Authorization: Bearer $ADM" -H 'Content-Type: application/json' -d '{}'
```

« Workflow name cannot be null or empty ». Et regardez la liste : elle est
revenue en `--- []`, c'est-à-dire du **YAML**, pas du JSON. `jq` la refuse avec
« Invalid numeric literal », et il le fait sur un realm vide comme sur un realm
peuplé, parce que le `---` est là dans les deux cas. Lisez cette erreur comme
« ce realm n'a aucun workflow » et vous passerez l'après-midi à chercher la
mauvaise chose.

La grammaire est un nom et des étapes, chacune nommant ce qu'elle `uses`. Le
verbe est la décision, pas la syntaxe :

```text
disable-user   suspend l'accès, garde le compte, garde les preuves
delete-user    retire le compte, et la trace de ce qu'il avait
```

Une revue a besoin que la seconde colonne existe. Une règle de cycle de vie qui
supprime détruit l'historique de l'accès en même temps que l'accès, sans
personne, à trois heures du matin, et plus jamais quelqu'un ne pourra répondre
à « qui avait la production en mars ». La notation refuse `delete-user` pour
cette seule raison.

## Ce que cela vous laisse

Trois habitudes, et elles survivent à ce produit :

- une mise à jour qui rend un succès ne prouve rien : relire l'état ;
- `401` n'est pas une réponse, c'est une famille ; le message dit laquelle ;
- avant d'automatiser un verbe destructeur, demander ce dont l'audit aura
  besoin après.

```bash
dsoxlab challenge iam-13-revue-des-acces
```
