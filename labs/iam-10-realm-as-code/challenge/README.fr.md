# Challenge : décrire le realm, l'appliquer, rattraper la dérive

`/opt/iam-lab/identifiants-lab.txt` **est le cahier des charges**. Il nomme le
realm à créer, son nom d'affichage, sa durée de jeton en secondes, ses rôles,
son groupe, les deux identifiants de clients, le nom de la variable qui doit
porter le secret du client confidentiel, le répertoire de travail, et la
version du provider à épingler. Les tests lisent ces valeurs dans ce fichier :
rien n'est codé en dur, d'aucun côté.

Terraform est installé. Le répertoire de travail est vide. Le realm n'existe
pas.

## Ce qui est attendu

1. Des fichiers `.tf` dans le répertoire de travail qui **épinglent la version
   du provider**, et un fichier d'état : le realm doit être décrit, pas
   seulement créé.
2. Le realm existant avec le nom d'affichage et la durée de jeton du cahier
   des charges, ses deux rôles, son groupe et ses deux clients.
3. Le client public exigeant **PKCE S256**.
4. `terraform plan -detailed-exitcode` qui rend **0** : ce qui tourne est ce
   qui est écrit.
5. Une dérive faite à la main qui est **corrigée** par une réapplication. Le
   test en introduit une lui-même, vérifie que le plan rend **2**, applique, et
   vérifie que la valeur est revenue.
6. **Aucun justificatif en clair** dans ce que vous avez écrit. Le test lit le
   mot de passe d'administration du socle et le secret réel du client par
   l'API, puis cherche les deux dans vos fichiers.
7. Le répertoire de travail **fermé aux autres**, à cause de ce que contient le
   fichier d'état.
8. Les realms `master` et `formation` intacts.

## Où vont les justificatifs

Le provider lit `KEYCLOAK_URL`, `KEYCLOAK_USER`, `KEYCLOAK_PASSWORD` et
`KEYCLOAK_REALM` dans l'environnement. Rien n'a besoin d'être écrit dans un
fichier. Le compte d'administration du socle est dans `/opt/socle-iam/.env`.

Le secret du client confidentiel passe par une variable Terraform, dont le
cahier des charges fixe le nom (`VARIABLE_SECRET_ATTENDUE`), transmise en
`TF_VAR_<nom>`. Le nom est imposé parce que la notation rejoue votre code et
doit pouvoir l'alimenter.

## Trois choses mesurées sur cette machine

**Le provider s'annonce « self-signed » au `terraform init`**, avec l'empreinte
de sa clef. Ce n'est pas une alerte : c'est la signature d'un éditeur qui n'est
pas HashiCorp. Le provider vit sous l'organisation `keycloak` sur GitHub.

**`plan -detailed-exitcode` rend 0 quand l'état correspond, 2 quand il diffère,
1 en cas d'erreur.** Jugez sur le code, et non en lisant la sortie.

**Le fichier d'état garde votre secret en clair, et sa sauvegarde est recréée
avec les droits par défaut à chaque application.** Donc `terraform.tfstate`
garde le mode que vous lui donnez, parce que l'outil écrit dans le fichier
existant, tandis que `terraform.tfstate.backup` revient en `644` chaque fois.
Protéger le fichier ne tient pas. Protéger le répertoire, oui.

## Deux cas d'échec que la notation attrape

**Un secret écrit en clair**, mot de passe d'administration ou secret de
client, dans un `.tf` ou un `.tfvars`. Le test connaît les vraies valeurs : il
ne cherche pas le mot « password », il cherche la valeur.

**Le cahier des charges appliqué sur le mauvais realm.** Le provider
s'authentifie contre un realm et en administre un autre. Le `realm_id` de
chaque ressource doit désigner le realm que vous décrivez.

```bash
dsoxlab check iam-10-realm-as-code   # noter
dsoxlab hint  iam-10-realm-as-code   # un indice, au prix de quelques points
```
