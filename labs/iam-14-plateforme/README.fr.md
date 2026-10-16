# Tutoriel : deux portes, et un drapeau ignoré en silence

Ce tutoriel ne fait pas le challenge. Il vous fait voir trois choses, sur des
clusters jetables que vous supprimez aussitôt, qui vous coûteraient chacune une
après-midi dans le challenge. Mesurées sur cette machine le 2026-10-16.

```bash
IDS=/opt/iam-lab/identifiants-lab.txt
REALM=$(grep '^REALM=' $IDS | cut -d= -f2-)
IP=$(grep '^IP_MACHINE=' $IDS | cut -d= -f2-)
CA=$(grep '^CA_IDP=' $IDS | cut -d= -f2-)
echo "machine $IP, realm $REALM, certificat du fournisseur $CA"
```

## 1. Le fournisseur ne se décrit pas pareil sur chaque porte

Le setup a posé un accès TLS devant le fournisseur. Les deux portes sont
ouvertes. Demandez à chacune qui elle dit être :

```bash
echo "par la porte HTTP :"
curl -s "http://127.0.0.1:8080/realms/$REALM/.well-known/openid-configuration" \
  | jq -r '"   iss  = \(.issuer)\n   jwks = \(.jwks_uri)"'

echo "par la porte TLS :"
curl -s --cacert "$CA" --resolve "idp.lab:8443:127.0.0.1" \
  "https://idp.lab:8443/realms/$REALM/.well-known/openid-configuration" \
  | jq -r '"   iss  = \(.issuer)\n   jwks = \(.jwks_uri)"'
```

Même realm, mêmes comptes, mêmes mots de passe, deux issuers différents. Le
fournisseur calcule son issuer depuis la requête qu'il a reçue : la porte à
laquelle vous frappez finit donc écrite dans chaque jeton qu'il vous remet.

Un cluster compare le `iss` d'un jeton à l'unique issuer qu'on lui a configuré.
L'une de ces deux portes est donc la bonne, et l'autre produit des jetons
parfaitement valides et systématiquement refusés. Rien, dans le jeton, n'a
l'air faux.

## 2. Un drapeau accepté et ignoré

Montez un cluster nu, sans aucune configuration d'identité :

```bash
k3d cluster create essai-tuto --servers 1 --agents 0 --api-port 6551
```

Donnez-lui maintenant un jeton qui n'existe pas, et demandez-lui qui il croit
que vous êtes :

```bash
kubectl --server https://127.0.0.1:6551 --insecure-skip-tls-verify \
  --token "ceci-n-est-pas-un-jeton" auth whoami
```

Lisez cette réponse attentivement. Elle dit `system:admin`, avec le groupe
`system:masters`, et elle précise que le moyen d'authentification était un
**certificat X509**. Vous avez passé un jeton. Il a été ignoré, parce que le
kubeconfig courant porte un certificat client et que c'est lui qui gagne.

C'est ainsi que l'on conclut que son intégration OIDC fonctionne. On la
configure, on l'éprouve avec `--token`, on obtient une réponse, et la réponse
venait de son propre certificat d'administration. Le contrôle passe avant que
le travail soit fait.

Le remède est de laisser le jeton seul en lice :

```bash
kubectl --kubeconfig /dev/null --server https://127.0.0.1:6551 \
  --insecure-skip-tls-verify --token "ceci-n-est-pas-un-jeton" auth whoami
```

Cette fois il échoue, ce qui est la réponse juste à un jeton que personne n'a
émis. Gardez `--kubeconfig /dev/null` pour tout ce que vous mesurez avec un
jeton, dans ce lab et après lui.

```bash
k3d cluster delete essai-tuto
```

## 3. Le serveur d'API refuse http en ne démarrant pas

Écrivez une configuration d'authentification qui désigne la porte HTTP, ce qui
est la chose naturelle à écrire puisque c'est la porte que tous les autres labs
utilisent :

```bash
sudo mkdir -p /etc/k3d-tuto
sudo tee /etc/k3d-tuto/auth.yaml > /dev/null <<CONF
apiVersion: apiserver.config.k8s.io/v1beta1
kind: AuthenticationConfiguration
jwt:
  - issuer:
      url: http://$IP:8080/realms/$REALM
      audiences:
        - kubernetes
    claimMappings:
      username:
        claim: preferred_username
        prefix: ""
CONF
echo "config écrite"
```

Essayez ensuite de démarrer un cluster qui la lit. Cela prend une minute, et la
minute est la leçon :

```bash
k3d cluster create essai-http --servers 1 --agents 0 --api-port 6552 \
  --no-rollback \
  --volume /etc/k3d-tuto:/etc/k3d-tuto@server:0 \
  --k3s-arg "--kube-apiserver-arg=authentication-config=/etc/k3d-tuto/auth.yaml@server:0" \
  --timeout 60s
```

Ce que vous obtenez est un délai dépassé : le nœud n'est jamais devenu prêt.
Rien ne dit pourquoi. La raison est dans le conteneur, et `--no-rollback` est
la raison pour laquelle ce conteneur existe encore quand vous l'interrogez :

```bash
docker logs k3d-essai-http-server-0 2>&1 \
  | grep -iE 'invalid authentication|URL scheme' | head -3
```

```text
Error: invalid authentication configuration: jwt[0].issuer.url:
Invalid value: "http://...": URL scheme must be https
```

C'est une seule phrase, et c'est toute l'explication. Sans `--no-rollback`,
`k3d` supprime le conteneur en nettoyant derrière lui, et il ne vous reste
qu'un délai dépassé sans raison : c'est là qu'on se met à suspecter la
mémoire, l'image, ou le réseau.

```bash
k3d cluster delete essai-http
sudo rm -f /etc/k3d-tuto/auth.yaml && sudo rmdir /etc/k3d-tuto
```

## Ce que cela vous laisse

- un fournisseur peut répondre sur plusieurs portes, et la porte est inscrite
  dans le jeton : vérifiez ce qu'il dit de lui-même avant de croire ce que vous
  avez supposé ;
- un moyen d'authentification que vous passez n'est pas forcément celui qui a
  servi, et la façon sûre d'en mesurer un est d'en faire le seul disponible ;
- un composant qui refuse en ne démarrant pas met sa raison dans ses propres
  journaux : gardez la pièce à conviction en vie assez longtemps pour la lire.

```bash
dsoxlab challenge iam-14-plateforme
```
