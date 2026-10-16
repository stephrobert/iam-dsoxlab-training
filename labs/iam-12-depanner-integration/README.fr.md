# Tutoriel : trois endroits où regarder, dans l'ordre

Ce tutoriel ne fait pas le challenge. Il vous montre les trois sources de
vérité dont vous disposez quand une intégration échoue, et il les montre sur
**votre propre intégration cassée**, puisque c'est ce que vous avez devant vous.

Rien ici ne répare. On lit d'abord, on agit après.

## 1. Ce que le fournisseur dit à l'écran

Jouez le parcours et lisez le message. Pas la page, le message :

```bash
MDP=$(grep '^MOT_DE_PASSE=' /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)
python3 /opt/iam-lab/outils/parcours.py \
  --depart http://127.0.0.1:9080/connexion \
  --utilisateur alice --mot-de-passe "$MDP" \
  --attendre-texte "Connecté en tant que alice" \
  | jq -r '"arrivee : \(.arrivee)", "texte   : \(.texte)"'
```

Lisez où il s'est arrêté, puis ce qu'il dit. Les deux ensemble en disent long :

- il s'est arrêté sur l'adresse du **fournisseur**, et parle d'un paramètre : le
  fournisseur a refusé la requête, avant que personne ne se connecte ;
- il s'est arrêté sur l'adresse de l'**application**, et l'application se
  plaint : le fournisseur a répondu, et l'application n'a pas aimé la réponse ;
- la page annonce `Sign in to Keycloak` au lieu de `Sign in to Formation IAM` :
  l'application parle à un tout autre realm.

Ce dernier cas mérite un second regard. Le titre de la page vient du nom
d'affichage du realm, et c'est la façon la plus rapide de remarquer qu'une
application frappe à la mauvaise porte.

## 2. Ce que le fournisseur a enregistré

L'écran montre un message à un utilisateur. Le journal d'événements garde
chaque tentative, avec la cause dans un champ lisible par une machine. Il est
activé sur ce realm, ce qui n'est pas le défaut :

```bash
KC=http://127.0.0.1:8080
U=$(grep '^KC_BOOTSTRAP_ADMIN_USERNAME=' /opt/socle-iam/.env | cut -d= -f2-)
P=$(grep '^KC_BOOTSTRAP_ADMIN_PASSWORD=' /opt/socle-iam/.env | cut -d= -f2-)
ADM=$(curl -s -X POST "$KC/realms/master/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  -d "username=$U" -d "password=$P" | jq -r .access_token)

curl -s "$KC/admin/realms/formation/events?max=5" \
  -H "Authorization: Bearer $ADM" \
  | jq -r '.[] | "\(.type)\terror=\(.error // "-")\t\(.details // {} | tostring[0:80])"'
```

Une ligne par tentative. Le champ `error` est tout l'intérêt : il nomme la cause
en un seul mot. Quatre d'entre eux comptent pour ce lab, et tous ont été mesurés
le 2026-10-16 :

| `error` | Ce que cela veut dire |
|---|---|
| `invalid_redirect_uri` | l'adresse de retour demandée par l'application n'est pas déclarée |
| `client_disabled` | le client existe et il est éteint |
| `invalid_client_credentials` | le client attend un secret, et l'application n'en a pas envoyé |
| `not_allowed` | le flux demandé par l'application est fermé sur ce client |

Et un cinquième cas ne laisse **aucune ligne** dans ce realm. Réfléchissez à ce
que cela veut dire avant de lire la suite : si l'application parlait à ce realm,
il y aurait une ligne. Pas de ligne veut dire qu'elle parle à un autre.

Regardez aussi le champ des détails. Sur `invalid_redirect_uri`, il porte l'URI
qui a été demandée, que vous pouvez alors comparer à ce que le client déclare :

```bash
curl -s "$KC/admin/realms/formation/clients?clientId=appli-notes" \
  -H "Authorization: Bearer $ADM" \
  | jq -r '.[0] | "declarees : \(.redirectUris)", "activee   : \(.enabled)",
                  "publique  : \(.publicClient)",
                  "flux code : \(.standardFlowEnabled)",
                  "pkce      : \(.attributes["pkce.code.challenge.method"])"'
```

Cinq lignes, et quatre des cinq pannes y sont visibles.

## 3. Ce que l'application dit d'elle-même

L'application a un avis aussi, et c'est la seule source pour la cinquième panne :

```bash
curl -s http://127.0.0.1:9080/etat | jq .
```

Lisez `issuer` et `client_id` : c'est ce que l'application croit interroger.
Comparez avec le realm que vous administrez vraiment. Et lisez
`derniere_erreur`, qui porte le refus du fournisseur mot pour mot quand
l'application est allée assez loin pour être refusée.

La configuration qu'elle lit est un fichier, et vous pouvez le voir :

```bash
cat "$(grep '^CONFIGURATION_APPLI=' /opt/iam-lab/identifiants-lab.txt | cut -d= -f2-)"
```

Trois clés. L'une d'elles peut être fausse, et si elle l'est, rien dans le
journal du fournisseur ne vous le dira, parce que le fournisseur n'a jamais
entendu parler de cette application.

## Une méthode, en quatre lignes

1. Jouez le parcours. Notez **où** il s'est arrêté et **ce qu'il** a dit.
2. Lisez les derniers événements. Le champ `error` nomme la cause, ou son
   absence vous dit que l'application est ailleurs.
3. Comparez ce que le client déclare avec ce que l'application demande.
4. Corrigez cette seule chose. Puis rejouez le parcours.

La quatrième étape est l'endroit où ce lab est réellement noté. Il y a cinq
façons de faire disparaître le symptôme sans corriger la cause, et les tests
vérifient chacune d'elles.

```bash
dsoxlab check iam-12-depanner-integration   # noter
dsoxlab hint  iam-12-depanner-integration   # un indice, au prix de quelques points
```
