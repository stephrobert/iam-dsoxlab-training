# Instructions Claude Code : `kubernetes-dsoxlab-training`

Catalogue de **micro-labs vérifiables** pour la formation Kubernetes du blog
`blog.stephane-robert.info`. Il est joué par la CLI **dsoxlab**, qui vit
ailleurs (`~/Projets/dsoxlab`) et dont ce dépôt n'est qu'un **fournisseur de
contenu**.

## Pourquoi ce dépôt existe

**CKA, CKAD et CKS sont entièrement pratiques.** Le candidat répare ou
construit sur un cluster réel ; il ne reconnaît pas une bonne réponse parmi
quatre. Un quiz prépare au vocabulaire, pas à l'épreuve.

La formation du blog compte plus de 1 700 questions et 76 labs attestés. Ces
attestations prouvent que **l'auteur** a vérifié. Ce dépôt donne à
**l'apprenant** de quoi se vérifier lui-même.

La question qui pilote le backlog n'est donc pas « combien de labs ? » mais :

> **Combien de compétences du blueprint peuvent être démontrées réellement ?**

## Règle non négociable : un lab s'éprouve dans les deux sens

Un test qui passe ne prouve rien tant qu'on n'a pas vu **échouer** ce qui doit
échouer. Avant tout commit d'un lab :

```bash
dsoxlab run   <id>    # l'état initial est posé
dsoxlab check <id>    # DOIT échouer : 0/100, le travail n'est pas fait
# puis la solution du formateur, sur la cible
dsoxlab check <id>    # DOIT passer : 100/100
```

Un lab dont les tests passent **avant** le travail ne mesure rien. C'est le
défaut le plus coûteux du domaine, et il ne se voit qu'ainsi.

**`scripts/valider-labs.py` fait ce cycle à votre place**, et un peu plus : il
photographie le cluster avant le lab, joue `run`, `check`, la solution, `check`,
puis `clean`, `run`, `check` pour prouver que le setup se rejoue, puis `clean`,
et compare le cluster à sa photographie. Un namespace oublié, un ClusterRole,
un taint ou un CoreDNS laissé à zéro replica rend le lab **ROUGE**, parce que
c'est le lab suivant qui en paierait le prix. Le résultat est écrit dans
`validation-labs.json`, et `check-labs-completude.py` le relit pour distinguer
« livrable » de « validé ».

```bash
python3 scripts/valider-labs.py --lab <id>
```

Le validateur a lui-même été éprouvé dans les deux sens : sur un `cleanup.yaml`
privé de sa suppression de namespace, il rend ROUGE et nomme les six objets
laissés.

### Les tests lisent l'état du système, jamais les commandes tapées

Le candidat arrive au résultat par le chemin qu'il veut. On interroge donc le
cluster et le nœud, pas un historique.

```python
# NON : on relit ce que l'apprenant a écrit
assert "apparmor_parser" in historique

# OUI : on interroge l'état réel
profils = json.loads(host.run("sudo aa-status --json").stdout)["profiles"]
assert profils["k8s-refuser-ecriture"] == "enforce"
```

### Un test par affirmation, dont un qui prouve vraiment

Vérifier qu'un profil est chargé et qu'un Pod le déclare ne prouve **pas** que
le confinement agit : un profil vide passerait. Le dernier test d'un lab doit
exercer **les deux côtés**, ce qui est interdit et ce qui reste permis.

## Un test « rien n'est cassé » est vrai AVANT le travail

C'est le défaut que ce dépôt a produit le plus souvent : **cinq fois dans la
seule journée du 2026-09-16**, sur cinq labs différents.

Un lab de durcissement ou de remédiation a deux exigences : la porte visée
doit se fermer, **et** le service doit continuer de rendre le sien. La
tentation est d'en faire deux tests. Or la seconde moitié est l'ÉTAT DE
DÉPART :

| Test écrit | Vrai avant le travail parce que |
|---|---|
| « le cluster répond » | le cluster répondait déjà |
| « les deux exemplaires tournent » | le Deployment tournait déjà |
| « le Dockerfile existe » | le setup l'a posé |
| « le témoin peut appeler chmod » | il n'a jamais été confiné |
| « le contrôle plane répond » | il n'a pas encore été touché |
| « les deux conteneurs montent un volume commun » | Kubernetes en projette un dans chacun |

Le dernier cas, mesuré le 2026-09-17, est le plus sournois, parce que rien ne
le laisse deviner à la lecture : **Kubernetes projette de lui-même le jeton du
ServiceAccount dans chaque conteneur**, sous un volume `kube-api-access-xxxxx`.
Un Pod qui ne déclare AUCUN volume en a donc un, monté des deux côtés, et
l'intersection des volumes montés n'est jamais vide. Le test passait avant le
travail, et c'est le validateur qui l'a trouvé. Tout test qui énumère les
volumes ou les montages d'un Pod doit écarter ce nom.

La forme juste est de **fusionner cette moitié dans le test final**, où elle
ne peut être atteinte qu'après le travail, et où elle prend tout son sens :
elle distingue un durcissement d'une panne. Un API server arrêté ferme le
profileur aussi sûrement qu'un flag bien posé.

> Avant d'écrire un test, se demander : « serait-il vert si le candidat ne
> faisait rien ? » Si oui, ce n'est pas un test, c'est une hypothèse du setup.

## Le catalogue a deux descriptions, et le trou est entre les deux

`labs/*/lab.yaml` dit **ce qui existe**. `meta.yml` dit **dans quel ordre le
jouer**. Chaque outil lit la sienne et a raison de son côté : rien ne
comparait les deux.

Mesuré le 2026-09-16, et cela a coûté deux labs :

- `cks-rbac-least-privilege` et `cks-audit-log-policy`, tous deux validés,
  ont disparu de `meta.yml` après une manipulation de branches. Ils
  restaient dans la table de couverture du README, qui part des `lab.yaml`,
  mais pas dans le parcours recommandé : un apprenant qui suit le parcours ne
  les aurait jamais joués ;
- pire, `labs/cks-rbac-least-privilege/` s'est retrouvé réduit à son seul
  sous-dossier `challenge/`. **Aucun contrôle ne l'a vu**, et c'est logique :
  `validate-structure` comme `check-labs-completude.py` énumèrent les labs par
  leur `lab.yaml`, donc un lab sans `lab.yaml` n'existe pas pour eux. Vérifié :
  un répertoire amputé posé à la main ne déclenche rien.

`tests/test_meta_declare_les_labs.py` ferme les deux trous, et il énumère les
**répertoires**, pas les `lab.yaml` : on ne peut pas constater l'absence d'un
fichier en partant de ce fichier.

**La méthode qui a causé cela**, et qu'il ne faut pas reproduire : enchaîner
`gh pr merge`, `git checkout main` et `git reset --hard origin/main` sans
regarder le résultat de chaque commande. Le `checkout` a échoué sur des
fichiers non commités, le `reset` s'est donc appliqué à la mauvaise branche.

> Après tout changement de branche, `git status` et le nombre de labs se
> regardent AVANT de continuer. Un `&&` enchaîné n'est pas une vérification.

## Un chiffre publié se lit à sa source, jamais par raisonnement

Les poids des domaines, les versions de curriculum, les seuils de réussite :
ce sont des données que **quelqu'un d'autre publie**. Elles ne se déduisent
pas, elles se lisent.

Mesuré le 2026-09-15, et cela a coûté cinq issues fausses : les poids de
*Cluster Setup* et *System Hardening* ont été échangés dans le backlog par une
« correction » appuyée sur une page de site et une intuition, avec un encadré
affirmant que la source avait été vérifiée. Elle ne l'avait pas été. Le PDF
officiel a tranché en deux commandes :

```bash
gh api repos/cncf/curriculum/contents --jq '.[].name'   # les versions publiées
curl -sSL -o cks.pdf "https://raw.githubusercontent.com/cncf/curriculum/master/CKS_Curriculum%20v1.34.pdf"
pdftotext cks.pdf - | grep -E '^[0-9]+%'
```

Ces chiffres vivent désormais **une seule fois**, dans `curriculums.yml`, avec
leur source et la date de la dernière confrontation au PDF.
`tests/test_curriculums.py` refuse toute mention du dépôt qui les contredit,
et il a été éprouvé en réintroduisant l'erreur exacte.

> Une affirmation du type « vérifié sur le site officiel » sans commande qui
> le montre vaut **zéro**. Si la vérification n'est pas reproductible, elle
> n'a pas eu lieu.

## L'architecture, et pourquoi elle n'est pas kind

**Cluster kubeadm vanilla sur VM KVM.** Décision de Stéphane du 2026-09-14.

Ce n'est pas une entorse à la **règle 11** de la formation, qui impose kind aux
**guides** pour que le lecteur suive sur son poste. C'est la réponse à sa
**règle 7**, qui reconnaît que certains faits **ne se prouvent pas dans un
conteneur**, kind partageant le noyau de l'hôte.

Mesuré le 2026-09-14 : sur un nœud kind, le kubelet refuse un Pod AppArmor avec
`Cannot enforce AppArmor: AppArmor is not enabled on the host`. Sur la VM,
`aa-status --enabled` répond OK.

Ce que les VM débloquent, et que la formation avait dû classer « non couvert » :

| Sujet | Pourquoi kind ne suffit pas |
|---|---|
| **AppArmor**, profils de confinement | le module n'est pas actif dans le nœud conteneurisé |
| **Montée de version kubeadm** | exige un control plane et des kubelets réels |
| **Durcissement de l'OS hôte**, accès réseau externe | relève de la machine, pas du cluster |
| **Point de métadonnées du nœud** | aucun cluster local n'en expose |
| **Diagnostic kubelet, pod statique, etcd** | exige systemd et de vrais services |

Les deux approches ne se concurrencent pas : **la formation enseigne, ce
catalogue éprouve**.

## Topologie

Déclarée dans `meta.yml`, provisionnée par `dsoxlab provision`.

| Hôte | Rôle | Distribution | RAM |
|---|---|---|---|
| `k8s-cp.lab` | control plane | Ubuntu 24.04 | 4 Go |
| `k8s-w1.lab` | worker | Ubuntu 24.04 | 2,5 Go |

Ubuntu 24.04 parce que **c'est ce que recommande le guide kubeadm publié** :
aligner le lab sur le guide évite à l'apprenant de traduire une procédure
pendant qu'il apprend la procédure.

### Trois pièges de topologie, chacun a coûté un cycle

- **Le nom du réseau tient en 9 caractères après `lab-`.** Le pont vaut
  `virbr-<réseau sans lab->`, et le noyau limite un nom d'interface à 15.
  `lab-kubernetes` échoue sur `Numerical result out of range`, message qui ne
  nomme ni le pont ni la limite. D'où `lab-k8s`. Remonté en amont,
  `stephrobert/dsoxlab#214`.
- **L'IP et la MAC dérivent de la POSITION dans `infra.hosts`.** Insérer un
  hôte au milieu réattribue les adresses des suivants, ce que libvirt refuse en
  cours de route. Tout nouvel hôte s'ajoute **en fin de liste**.
- **Aucun point d'accroche après le provisionnement.** Le socle partagé est
  donc inclus par *chaque* `setup.yaml`. Remonté en amont,
  `stephrobert/dsoxlab#213`.

## Le socle partagé

`shared/kubeadm-cluster.yml` installe un cluster kubeadm 1.37 : le control
plane, puis chaque worker que `meta.yml` déclare avec `role: worker`, préparé
et joint **par délégation** depuis le play du control plane. Un lab n'a donc
jamais à connaître la topologie. Chaque `setup.yaml` inclut le socle, dans
un play sur `lab_target` :

```yaml
- name: Installer le socle, le cluster kubeadm du catalogue
  ansible.builtin.include_tasks: ../../shared/kubeadm-cluster.yml
```

Les tâches communes à tout nœud, swap, modules, containerd, paquets, vivent
dans `shared/noeud-kubernetes.yml`, inclus une fois pour le control plane et
une fois par worker. Le taint du control plane est retiré même avec un
worker : un lab qui n'a besoin que d'un nœud doit continuer à tourner si le
worker manque, et les labs qui enseignent les taints posent les leurs.
Décision de l'issue #2, joint le 2026-09-14.

**Chaque tâche porte sa propre idempotence, et c'est délibéré.** La première
version gardait tout le fichier derrière un unique « le cluster répond-il
déjà ? ». Un premier passage a échoué **après** `kubeadm init` mais **avant** le
CNI ; au passage suivant, la garde a vu un cluster qui répond et a tout sauté.
Le nœud serait resté `NotReady` indéfiniment.

> Une garde grossière transforme un échec partiel en **échec permanent**.

Ne jamais réintroduire de `when:` global sur ce fichier.

## Écrire un lab

```bash
dsoxlab new lab <id> --runtime vm
```

Convention d'identifiant : `<examen>-<sujet>`, en minuscules, en français.
Exemple : `cks-apparmor-confiner-un-pod`.

### Ce que chaque lab doit porter

| Fichier | Rôle |
|---|---|
| `lab.yaml` | contrat : `level` = le **domaine du blueprint**, `doc_url` = la leçon jumelée |
| `setup.yaml` | playbook qui pose l'état initial, inclut le socle |
| `cleanup.yaml` | défait ce que le lab a créé, **laisse le cluster en place** |
| `scenario.md` | la situation, l'objectif, les repères. Pas la solution |
| `challenge/tests/test_functional.py` | pytest + testinfra, lit l'état du système |
| `challenge/hints.yaml` | indices **base64**, bilingues, avec un coût |
| `challenge/solution.sh` | la solution du formateur, rejouable |

Quatre pièges mesurés, chacun a coûté un cycle :

- **La solution est lue par `bash -s` depuis l'entrée standard**, c'est ainsi
  que le validateur la joue sur la cible. Tout `ssh` qu'elle contient porte
  donc `-n`, sinon il avale le reste du script comme entrée : rien après lui
  ne s'exécute, et le script rend 0.
- **`fixtures/prepare.sh` trace dans `/var/log/dsoxlab-prepare.log`** sur le
  nœud, avec `set -x`, parce que dsoxlab ne rend que « non-zero return code »
  quand il échoue. Le validateur relit ce fichier. Un nouveau `prepare.sh`
  reprend l'en-tête d'un lab existant.
- **Un objet à jour dans l'API n'est pas encore un effet sur le nœud.**
  Mesuré le 2026-09-15 sur `cka-capstone-portail` : une seconde après le
  passage d'un Service en NodePort, l'API rend bien `type: NodePort` et son
  `nodePort`, mais la chaîne iptables `KUBE-NODEPORTS` est **encore vide**.
  kube-proxy programme la règle après avoir été notifié, en 1048 ms au
  premier passage et une douzaine de millisecondes ensuite. La solution
  interrogeait le port immédiatement et rendait le lab ROUGE alors que le
  travail était juste. **Un test qui mesure un effet réseau attend cet effet**,
  avec un budget borné : sans cette attente, il recale un candidat dont la
  correction est bonne, et un faux négatif vaut pire qu'un test absent.
- **Un désinstalleur officiel ne reprend pas ce qu'il a essaimé.** Mesuré le
  2026-09-16 sur `cks-istio-mtls-lockdown` : `istioctl uninstall --purge`
  retire bien les CRD, les webhooks et le namespace, et le lab est quand même
  rendu **ROUGE**. istiod pousse son certificat de CA racine dans un ConfigMap
  `istio-ca-root-cert` de **chaque** namespace, `kube-system` compris, et le
  purge laisse ces copies. Chaque installation générant un nouveau CA, le
  ConfigMap n'est pas seulement laissé : son contenu **change** d'un passage à
  l'autre, ce que la photographie du validateur a nommé au caractère près.
  Tout composant installé dans le cluster, maillage, opérateur ou contrôleur
  d'admission, est à supposer essaimant : la question n'est pas « ai-je
  désinstallé ? » mais « qu'a-t-il écrit ailleurs ? ».

`level` reprend le **domaine officiel** mot pour mot (`system-hardening`,
`troubleshooting`, `supply-chain-security`…) : c'est ce qui permet de répondre
à la question qui pilote le dépôt.

`doc_url` pointe la leçon du blog que le lab éprouve. Un lab sans leçon jumelée
est un lab qui enseigne au lieu d'éprouver : c'est le rôle du site.

### Les indices sont encodés

`challenge/hints.yaml` porte `text_fr` et `text_en` en **base64**, pour qu'un
apprenant n'y accède pas en ouvrant le fichier. Quatre indices de coût croissant
sont un bon dosage, du plus vague au plus explicite, sans jamais donner le YAML
complet.

### Les collections Ansible se déclarent

Toute collection hors `ansible.builtin` va dans `requirements.yml`. Le
catalogue Linux a perdu du temps sur un `rc=4` qui ressemblait à un problème de
réseau, causé par une collection installée par hasard sur le poste de
développement.

## Transposer un lab de K8sExamLab

`~/Projets/K8sExamLab` est l'ancêtre archivé de dsoxlab. Il porte **61 labs
CKA/CKAD/CKS** que le moteur courant rejette, mais dont la substance est
récupérable : **317 checks**, **183 indices déjà en base64**, 41 mises en
situation, et une bibliothèque de **1954 lignes couvrant 144 types de check**,
vérifiée portable sur kubeadm.

### L'outillage

```bash
python3 scripts/convertir-k8sexamlab.py --lab <chemin dans K8sExamLab>
python3 scripts/proposer-doc-url.py           # quelle leçon du blog jumeler
python3 scripts/check-labs-completude.py      # ce qui reste à faire
```

Le convertisseur fait la partie mécanique et **laisse des marqueurs
`A_COMPLETER`** là où un humain doit passer. Il ne prétend pas finir le travail.

### La procédure, dans cet ordre

1. **Transposer.** Le lab apparaît sous `labs/<examen>-<id>/`.
2. **Jumeler la leçon.** `proposer-doc-url.py` propose et donne un score ; il
   ne décide pas. Un lab sans correspondance signale souvent que **la formation
   n'a pas de leçon sur ce sujet** : cela remonte au backlog du blog, pas ici.
3. **Réécrire `scenario.md` en français.** Une consigne mal traduite est pire
   qu'une consigne en anglais : elle se lit sans méfiance.
4. **Traduire les indices.** `text_fr` est une copie de l'anglais tant que
   personne n'est passé, et le contrôle de complétude le voit.
5. **Écrire `cleanup.yaml`.** L'ancien format n'en avait pas. Lister ce que le
   lab crée, namespaces compris ; le cluster, lui, reste en place.
6. **Jouer le lab**, et c'est l'étape qu'aucun script ne remplace.

### Ce que la transposition révèle, et pourquoi il faut jouer

Le premier lab transposé, `troubleshoot-dns`, a livré **trois défauts**, dont
deux dans le convertisseur et un dans le lab hérité. Le troisième est le plus
instructif : son `setup` passe CoreDNS à zéro replica, et sa solution porte le
commentaire

> `# CoreDNS is already running in a fresh cluster, no fix needed`

**La solution contredit son propre setup.** Ce lab n'a jamais été joué de bout
en bout. Rien, dans le fichier, ne le laissait deviner.

Il faut donc supposer que **d'autres labs hérités portent le même défaut**, et
qu'un lab transposé qui « passe la structure » ne prouve rien. Les deux autres
défauts trouvés valent aussi d'être connus : le répertoire `solution/` porte
parfois des fichiers compagnons qu'il faut copier en entier, et un générateur
de tests qui joint des arguments sans virgule produit du Python valide mais
faux, puisque les littéraux adjacents se concatènent.

### Un lab est fini quand

```bash
python3 scripts/check-labs-completude.py --check   # exit 0
dsoxlab validate-structure                         # exit 0
python3 scripts/valider-labs.py --lab <id>         # VALIDE : 0, puis 100, rejouable, sans trace
```

Les deux premiers contrôles sont mécaniques et ne disent **rien** de la justesse
du lab. Seul le troisième l'établit, et il ne se ferme qu'en fermant l'issue du
lab avec ses mesures.

### Le piège de fond : ces labs visent la 1.34

56 labs sur 61 déclarent `kubernetes_version: "1.34"`, cinq la 1.35. La
formation enseigne la **1.37**, et l'écart n'est pas théorique : sur une seule
journée d'audit du blog, la 1.37 a réécrit des messages d'events, supprimé
`etcdctl snapshot status` et déplacé le sidecar Istio dans `initContainers`.

Un check hérité qui cherche une chaîne de caractères dans une sortie est donc
**suspect par défaut**. Le rejouer est la seule façon de trancher.

## Style de rédaction

Le français du blog : clair, pragmatique, sans jargon inutile.

- **Pas d'emoji**, pas de tiret cadratin dans ce que l'apprenant LIT :
  `scenario.md`, `README.md`, les indices, les messages d'assertion.
  `conftest.py` fait exception, il est repris verbatim du catalogue Linux
  et le faire diverger coûterait plus que le peu qu'il contient.
- **Les messages d'assertion enseignent.** Un test qui échoue doit dire ce qui
  ne va pas et pourquoi, pas seulement ce qui était attendu. C'est souvent le
  seul texte que l'apprenant lira attentivement.
- Le `scenario.md` décrit une **situation**, pas une liste de commandes. Un
  candidat à l'examen reçoit un contexte et un objectif, jamais un mode
  d'emploi.

## Cycle de vie

```bash
export LAB_HOME=$PWD
dsoxlab use --provider kvm
dsoxlab provision              # crée les VM, une fois
dsoxlab run   <id>             # pose l'état initial et ouvre la session
dsoxlab check <id>             # tests + score
dsoxlab reset <id>             # revient à l'état initial
dsoxlab clean <id>             # défait le lab, garde le cluster
dsoxlab destroy                # rend les VM, libère ~6,5 Go
```

`dsoxlab validate-structure` refuse un lab non conforme, et c'est le premier
contrôle à lancer après toute édition.

## Commits

Messages en français, sujet factuel qui dit **ce qui a changé et pourquoi**,
pas un préfixe conventionnel. Le corps raconte ce qui a été mesuré, y compris
les mesures jetées en route : elles valent souvent plus que le résultat.

## Ce dépôt n'est pas la CLI

Un défaut du moteur se corrige **dans `~/Projets/dsoxlab`**, ou se remonte en
issue. Ne jamais contourner une limite de la CLI par un bricolage local sans
l'avoir d'abord signalée en amont.

## État et suite

Le backlog vit dans `todo/ROADMAP-LABS.md`.
