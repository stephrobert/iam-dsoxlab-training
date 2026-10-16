# Tutoriel : ouvrir l'export et compter ce qu'il y a dedans

Ce tutoriel ne fait pas le challenge. Il ouvre un export, sur votre propre
instance, et compte ce qu'il contient, parce que tout ce dont ce lab parle est
visible dans ce seul fichier et invisible dans son nom. Mesuré sur cette
machine le 2026-10-16.

```bash
IDS=/opt/iam-lab/identifiants-lab.txt
REALM=$(grep '^REALM=' $IDS | cut -d= -f2-)
PROD=$(grep '^REPERTOIRE_PROD=' $IDS | cut -d= -f2-)
ENVP=$(grep '^ENV_PROD=' $IDS | cut -d= -f2-)
BASE=$(grep '^CONTENEUR_BASE=' $IDS | cut -d= -f2-)
KC=$(grep '^CONTENEUR_KEYCLOAK=' $IDS | cut -d= -f2-)
URL=$(grep '^URL_PROD=' $IDS | cut -d= -f2-)
echo "instance $URL, realm $REALM, base dans $BASE"
```

## 1. Le code de sortie dit une chose, le répertoire en dit une autre

Exportez depuis le conteneur en marche, ce qui est la chose évidente à
essayer :

```bash
sudo docker exec $KC /opt/keycloak/bin/kc.sh export \
  --dir /tmp/essai --realm "$REALM" > /tmp/essai.log 2>&1
echo "code de sortie : $?"
tail -3 /tmp/essai.log
```

Il sort en **1**, et la raison n'a rien à voir avec l'export : la commande
démarre un serveur pour faire son travail, et ce serveur ne peut pas prendre
son port de gestion, que le Keycloak en service occupe déjà.

Regardez maintenant s'il a fait le travail quand même :

```bash
sudo docker exec $KC ls -la /tmp/essai/
```

Les fichiers sont là. Un script qui croit le code de retour conclut que
l'export a échoué ; un script qui liste le répertoire conclut qu'il a réussi.
Les deux ont lu quelque chose de réel, et aucun n'a lu le fichier.

La façon propre est un conteneur jetable, qui ne publie aucun port :

```bash
sudo mkdir -p /tmp/propre && sudo chown 1000:0 /tmp/propre
cd "$PROD" && sudo docker compose -f compose.yaml --env-file "$ENVP" \
  run --rm --no-deps -v /tmp/propre:/exp \
  keycloak export --dir /exp --realm "$REALM" > /tmp/propre.log 2>&1
echo "code de sortie : $?"
sudo ls -la /tmp/propre/
```

Le `chown 1000:0` n'est pas décoratif : le processus de cette image tourne sous
l'uid 1000, et un répertoire qui appartient à root vous vaut « Error during
export/import: (Permission denied) » après dix secondes de démarrage.

## 2. Comptez ce qu'il y a dans chaque fichier

Deux fichiers. Ouvrez les deux et comptez :

```bash
for f in /tmp/propre/*.json; do
  echo "── $(basename $f) : $(sudo stat -c %s $f) octets"
  sudo cat "$f" | jq -r '"   nb de clefs de premier niveau : \(keys | length)
   une clef users ?              : \(has("users"))
   comptes                       : \(.users | length? // 0)
   clients                       : \(.clients | length? // 0)
   flux d authentification       : \(.authenticationFlows | length? // 0)"'
done
```

Le fichier du realm porte 120 clefs de premier niveau : les clients, les flux,
les clefs de signature, tout ce que vous reconnaîtriez comme de la
configuration. Et `has("users")` y vaut **false**. Pas une liste vide : la clef
n'y est pas. Les comptes sont dans l'autre fichier, celui au nom ennuyeux,
celui qu'on laisse derrière quand on copie « l'export » dans un répertoire.

Regardez le nombre de clefs, car il dit quelque chose que les tailles ne disent
pas. Le fichier des comptes en a exactement **deux**, `realm` et `users`. Cette
clef `realm` est un nom, pas le realm : un script qui trie les deux fichiers en
demandant « celui-ci a-t-il une clef realm » les rangera tous les deux du côté
de la configuration et conclura que l'export contient ses comptes. C'est une
vraie erreur, elle a été commise en écrivant ce tutoriel, et c'est la mesure
ci-dessus qui l'a attrapée.

Regardez ce que ce second fichier porte sur chaque compte :

```bash
sudo cat /tmp/propre/"$REALM"-users-0.json | jq -r '.users[0] |
  "   compte              : \(.username)
   des credentials ?   : \(has("credentials"))
   type                : \(.credentials[0].type)
   le secret est la ?  : \((.credentials[0].secretData // "") | length > 0)"'
```

Des empreintes de mots de passe. Ce fichier est un fichier de secrets, et
`0644` dans un répertoire partagé est la façon dont ils finissent quelque part
où vous ne les voulez pas.

## 3. Ce qu'aucun fichier d'export ne contient

Demandez à l'export ce qu'il sait des événements, puis demandez à la base :

```bash
echo "clefs de l export qui parlent d evenements :"
sudo cat /tmp/propre/"$REALM"-realm.json \
  | jq -r '[keys[] | select(test("vent"; "i"))] | "   \(.)"'

echo "et dans la base :"
for t in event_entity admin_event_entity user_entity credential; do
  n=$(sudo docker exec $BASE psql -U keycloak -d keycloak -tAc \
    "select count(*) from $t")
  printf '   %-20s %s\n' "$t" "$n"
done
```

Les clefs d'événements de l'export sont des **réglages** : les événements
sont-ils activés, quels types sont enregistrés. Les événements eux-mêmes sont
des lignes dans la base, et aucune option d'export ne les emmène.

C'est tout l'argument de ce lab en deux commandes. Un export décrit comment le
fournisseur est configuré. Une sauvegarde de la base contient ce qui s'est
passé. La question que pose un auditeur porte toujours sur ce qui s'est passé.

```bash
sudo rm -rf /tmp/propre /tmp/propre.log /tmp/essai.log
sudo docker exec $KC rm -rf /tmp/essai
```

## Ce que cela vous laisse

- une commande peut échouer et faire son travail quand même : lisez le
  résultat, pas le code de retour ;
- « l'export », c'est souvent plusieurs fichiers, et celui qui compte est
  rarement celui qui porte le nom évident ;
- la configuration et l'histoire sont deux choses différentes, et une seule des
  deux se reconstruit après coup.

```bash
dsoxlab challenge iam-09-sauvegarde-montee-version
```
