# Tutoriel : trois mécanismes à voir fonctionner

Ce tutoriel ne fait pas le challenge. Il vous fait voir agir, sur des exemples
jetables, les trois mécanismes dont le challenge a besoin. Les noms employés
ici ne sont pas ceux du challenge, et c'est voulu : vous devrez transposer.

Travaillez dans un répertoire temporaire, pour ne rien laisser derrière vous :

```bash
cd "$(mktemp -d)"
```

## 1. Un service qui attend qu'un autre soit prêt

Deux conteneurs qui démarrent ensemble ne démarrent pas pour autant dans le bon
ordre. Un service qui parle à une base doit attendre que la base **accepte des
connexions**, ce qui arrive bien après que son conteneur a démarré.

Compose sait exprimer cela, mais seulement si la dépendance porte une
**condition** et si la base déclare une **sonde de santé**. Voyons les deux sur
un exemple sans rapport avec le challenge.

```yaml
# compose.yaml, dans votre répertoire temporaire
name: demo-horloge

services:
  horloge-db:
    image: postgres:18.6
    environment:
      POSTGRES_PASSWORD: demo
      POSTGRES_DB: horloge
      POSTGRES_USER: horloge
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U horloge -d horloge"]
      interval: 3s
      retries: 10

  horloge:
    image: alpine:3.22
    command: ["sh", "-c", "echo 'la base etait prete a' $(date -Iseconds); sleep 5"]
    depends_on:
      horloge-db:
        condition: service_healthy
```

Lancez-le, et regardez l'ordre dans lequel les choses arrivent :

```bash
docker compose up
```

`horloge` n'affiche sa ligne qu'une fois la base déclarée saine. Retirez
maintenant la condition, en remplaçant le bloc `depends_on` par la forme
courte, et relancez :

```yaml
    depends_on:
      - horloge-db
```

```bash
docker compose down -v && docker compose up
```

Cette fois, `horloge` parle tout de suite : Compose a seulement attendu que le
conteneur de la base **démarre**, pas qu'elle soit prête. La différence est
invisible sur un `echo`, et elle ne l'est plus du tout pour un service qui
ouvre une connexion et abandonne quand elle est refusée.

Rangez cet exemple avant de passer à la suite :

```bash
docker compose down -v
```

## 2. Où un serveur dit s'il va bien

Un service en production expose son état ailleurs que sur le port de son
application. Le mélange serait une faute : la santé et les métriques
intéressent l'exploitant, pas le visiteur, et les publier au même endroit les
rendrait accessibles à tous.

Essayez le principe sur un service quelconque :

```bash
docker run -d --name demo-sonde -p 18080:80 nginx:1.29-alpine
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18080/
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18080/etat
docker rm -f demo-sonde
```

Le premier appel rend `200`, le second `404` : ce serveur n'a pas de point
d'état, et rien n'indique qu'il va bien autrement que par le fait de répondre.

Keycloak, lui, en a un, et il vit sur un **port distinct** du port applicatif.
Ce port existe toujours, mais le point d'état n'est servi que si la
configuration l'autorise. La page d'installation du site nomme la variable qui
l'active, et le port concerné.

## 3. Créer un compte par l'API, sans passer par l'écran

La console web d'administration est agréable et ne se scripte pas. Tout ce
qu'elle fait, l'API d'administration le fait aussi, et c'est par elle que
l'exploitation passe.

Le principe tient en deux temps : obtenir un jeton avec un compte qui a le
droit, puis s'en servir. Voyons-le sur un service public de démonstration, pour
ne toucher à rien chez vous :

```bash
# Un jeton, avec un compte et un mot de passe, contre un point d'accès connu
curl -s -X POST https://httpbin.org/post \
  -d grant_type=password -d client_id=demo-cli \
  -d username=jean-meteo -d password=bulletin \
  | jq '.form'
```

La réponse vous renvoie ce que vous avez envoyé : la forme de la requête est
là, c'est tout ce qui nous intéresse. Contre un vrai serveur, cette requête
rend un `access_token`, que l'on présente ensuite dans un en-tête :

```bash
curl -s https://httpbin.org/headers \
  -H "Authorization: Bearer un-jeton-de-demonstration" \
  | jq '.headers.Authorization'
```

Deux choses à retenir pour le challenge, et qui surprennent souvent.

L'administrateur du **serveur** ne vit pas dans le même realm que les comptes
applicatifs. Un compte créé dans un realm administre ce realm, pas le serveur.

Et le compte de démarrage n'est pas un compte comme les autres : son mot de
passe est passé au conteneur par une variable d'environnement, donc lisible par
`docker inspect`. C'est pour cela qu'il est dit temporaire.

## Ce que le challenge demande maintenant

Vous avez vu une dépendance conditionnée par une sonde, un point d'état sur un
port séparé, et la création d'un compte par une API. Le challenge vous demande
de les assembler pour de vrai, sur Keycloak, et de retirer derrière vous ce qui
ne doit pas rester.

```bash
dsoxlab check iam-02-keycloak-installer   # valide
dsoxlab hint  iam-02-keycloak-installer   # un indice, au prix de points
```
