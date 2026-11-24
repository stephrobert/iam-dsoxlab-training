# L'application qui ne parlera pas OIDC

## La situation

L'entreprise partenaire exploite un outil de gestion documentaire. Il est
ancien, il fonctionne, et il survivra à tous ceux qui participent à cette
décision. Il parle SAML, et il ne parlera rien d'autre : il n'y a pas de budget
pour cela, et aucune raison.

Votre fournisseur parle SAML aussi. Celui de tout le monde le parle, parce que
des applications comme celle-là existent dans toutes les entreprises, et que ce
sont souvent les plus importantes.

Il faut donc les présenter l'un à l'autre, et la façon qu'a SAML de le faire est
un échange de **métadonnées**. Chaque côté publie un document qui dit qui il
est, où il écoute, et quel certificat signe ce qu'il envoie. Aucun des deux ne
devine quoi que ce soit de l'autre.

Puis il y a la partie dont les résumés ne parlent pas. SAML ne redirige pas un
navigateur comme OIDC le fait. Il lui remet un formulaire et le lui fait
soumettre tout seul, deux fois, et l'assertion voyage dedans. C'est pourquoi une
intégration SAML ne se dépanne pas avec une trace de redirections, et pourquoi
un navigateur fait partie du protocole plutôt que d'en être une commodité.

Ce qu'on vous donne : votre fournisseur avec un compte et un groupe, et un
second realm qui tient le rôle de l'outil du partenaire, vide. Ce que vous
faites : les deux côtés de l'échange. Le client qui émet des assertions signées,
et le fournisseur d'identité qui les consomme.

Ratez-le de la bonne façon et vous le verrez : l'outil du partenaire demandera à
votre utilisateur de saisir son propre nom. Cela veut dire que l'assertion est
arrivée, qu'elle a été acceptée, et qu'elle n'en disait pas assez.

## Les deux côtés d'un échange SAML

Deux realms sur `idp.lab`, servis par le même Keycloak.

| Realm | Rôle | État |
|---|---|---|
| `formation` | **émetteur** des assertions | porte `alice` et le groupe `devops` |
| `partenaire-sp` | **consommateur**, qui tient le rôle de l'outil du partenaire | vide, avec son propre groupe `devops` et un client OIDC |

`/opt/iam-lab/identifiants-lab.txt` porte l'identifiant d'entité du
consommateur, son adresse de réception d'assertion, l'alias attendu, l'URL des
métadonnées de l'émetteur, et le compte de test.

L'application témoin tourne déjà sur le port `9080`, pointée sur le
**consommateur**. Elle demande directement le fournisseur d'identité nommé
`saml-formation`, et vous ne verrez donc pas la page de connexion du
consommateur.

### Ce qui est attendu

**Côté émetteur**, dans `formation` :

1. Un **client SAML** dont l'identifiant est l'identifiant d'entité du
   consommateur, avec l'adresse de réception du consommateur en redirection.
2. Des **assertions signées**, avec un algorithme qui n'est pas SHA-1.
3. Des mappeurs qui portent l'**adresse, le prénom, le nom** et
   l'**appartenance aux groupes** dans l'assertion.

**Côté consommateur**, dans `partenaire-sp` :

4. Un **fournisseur d'identité SAML** d'alias `saml-formation`, activé, qui
   **exige** des assertions signées et **vérifie** la signature contre le
   certificat de l'émetteur.
5. Des mappeurs qui reprennent ces attributs sur le compte.
6. Un mappeur qui range le compte dans le groupe `devops` quand l'assertion le
   dit.

Puis une connexion, qui crée le compte.

### Ce qui est prouvé, et comment

Aucun test ne lit une assertion XML. Ils lisent ce que chaque côté déclare, puis
ils **jouent tout le parcours** comme un navigateur le ferait, et enfin ils
lisent le compte que le consommateur a obtenu :

- le client existe avec le bon identifiant d'entité et signe ses assertions ;
- le consommateur exige et vérifie la signature, contre le certificat de
  l'émetteur, pour le bon émetteur ;
- le parcours se termine sur l'application qui affiche le nom de l'utilisateur ;
- le compte porte l'adresse, le prénom et le nom ;
- le compte est dans `devops`.

### Contraintes

- L'alias est **`saml-formation`**. Il décide de l'adresse de réception du
  consommateur, que le client de l'émetteur doit déclarer, et l'application
  témoin le nomme.
- Le consommateur ne signe pas ses demandes. Exiger sa signature ferait refuser
  toutes les connexions.
- Lisez le certificat de l'émetteur dans ses **métadonnées**. Ailleurs, c'est un
  autre certificat, et le consommateur rejetterait toutes les assertions.

### Trois choses mesurées, pour ne pas y perdre une après-midi

**L'adresse seule ne suffit pas.** Sans le prénom et le nom, le consommateur
s'arrête sur « Update Account Information » et la connexion n'aboutit jamais.
Rien ne vous dit lequel des trois manque.

**Les groupes n'arrivent pas tout seuls.** Le mappeur d'appartenance de
l'émetteur les met dans l'assertion, et le compte arrive quand même sans aucun
groupe. Le consommateur a besoin de son propre mappeur pour lire l'attribut et
désigner le groupe, et ce groupe doit déjà exister dans son realm : un mappeur
n'en crée pas.

**`syncMode` décide si un mappeur s'applique à un compte déjà lié.** Sur un
compte existant, un mappeur en `INHERIT` ne réapplique rien, ce qui ressemble
trait pour trait à un mappeur qui ne fonctionne pas. Si vous dépannez un
mappeur, supprimez le compte lié et reconnectez-vous.

```bash
dsoxlab check iam-06-federation-saml   # noter
dsoxlab hint  iam-06-federation-saml   # un indice, au prix de quelques points
```
