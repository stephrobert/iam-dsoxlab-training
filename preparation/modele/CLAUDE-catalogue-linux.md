# Instructions Claude Code : `linux-dsoxlab-training`

Ce dépôt est un **fournisseur de labs** pour la CLI `dsoxlab`. Il contient le
catalogue Linux (84 labs) de la formation publiée sur
[www.stephane-robert.info](https://www.stephane-robert.info). Il ne contient
**aucun** code de moteur : la CLI vit dans `~/Projets/dsoxlab/`.

Ce fichier n'est **pas** versionné (il est listé dans `.git/info/exclude`).

> **Ce document décrit le code, pas l'intention.** Réécrit intégralement le
> 2026-07-27 depuis les sources, après avoir constaté qu'il documentait un
> contrat **abandonné et aujourd'hui rejeté par le validator** : `runtime/kvm.sh`,
> `runtime/shell.sh`, `cleanup.sh`, `Makefile` par lab, `runtime.host`,
> `make bootstrap/provision/verify-conn/restore`, un compte de service `student`,
> des IP codées en dur, et un chemin personnel `/home/bob/Projets/linux-training`
> donné en exemple à recopier. Un lab écrit d'après l'ancienne version de ce
> fichier était **refusé par `dsoxlab validate-structure`**.
>
> En cas de doute, le code fait foi : celui de `dsoxlab` pour le contrat, celui
> des labs existants pour les conventions. Ce fichier est à corriger, pas à
> contourner.

---

## Règles non négociables

### 1. On tire `main`, on crée la branche, **puis** on code

Dans cet ordre, **avant la première modification** :

```bash
git switch main && git pull
git switch -c <type>/<sujet-court>
```

Brancher après coup ne marche que tant que rien ne diverge. La branche est
gratuite avant, coûteuse après.

- **Commit et `git push` uniquement quand l'utilisateur le demande.** Sans
  demande, s'arrêter à « prêt à committer » et lister ce qui a changé.
- Aucun `gh pr create`, `gh release create`, `git push --tags` **autonome**.
  Sur demande explicite, la PR se crée par l'outil MCP GitHub (`gh pr create`
  est refusé par le gate de permissions) en remplissant réellement le template.
- Jamais de commit direct sur `main`.

### 2. Ne jamais livrer la solution

L'apprenant doit chercher. Deux conséquences mécaniques :

- **Les solutions sont chiffrées** avec `ansible-vault`, sous
  `solution/linux/<section>/<lab>/`, et le mot de passe (`.vault-pass` à la
  racine) est gitignoré. Un fichier de solution en clair est un bug, et
  `tests/test_solutions_chiffrees.py` échoue si l'un d'eux passe en clair.
- **Le tutoriel ne donne jamais la réponse du challenge** (voir « Écrire le
  `README.fr.md` » plus bas). C'est la règle la plus violée, et la plus coûteuse :
  un tutoriel qui construit la réponse bloc par bloc vide le challenge de tout
  intérêt.

### 3. Zéro script shell d'orchestration

Le validator de `dsoxlab` **refuse** un lab qui contient l'un de ces fichiers :

| Fichier interdit | À la place |
| --- | --- |
| `cleanup.sh` | `cleanup.yaml` (playbook Ansible) pour un lab `vm` |
| `runtime/kvm.sh`, `runtime/incus.sh` | `setup.yaml` (playbook Ansible) |
| `runtime/shell.sh` | `runtime.workdir` + `runtime.fixtures` dans `lab.yaml` |
| `Makefile` | rien : `dsoxlab` pilote tout |

Il n'y a **plus aucun `make`** dans ce dépôt. `make bootstrap`, `make provision`,
`make verify-conn`, `make restore` n'existent pas : ce sont `dsoxlab provision`,
`dsoxlab status`, `dsoxlab reset`.

### 4. La validation prouve l'état, elle ne fait pas confiance

On ne vérifie jamais qu'une commande a été tapée. On vérifie l'**état produit**,
interrogé de façon structurée.

```python
# NON : on relit ce que l'apprenant a écrit, on ne prouve rien
assert "PermitRootLogin no" in host.file("/etc/ssh/sshd_config").content_string

# OUI : on interroge l'état réel du service
assert host.run("sshd -T").stdout.count("permitrootlogin no") == 1
```

Par ordre de force croissante :

1. **Le fichier est conforme** (le plus faible : un fichier n'est pas un état).
2. **Le service voit la configuration** : `sshd -T`, `systemctl show`,
   `getenforce`, `firewall-cmd --list-all`, `lvs`, `findmnt`.
3. **Le comportement est celui attendu** : le port répond, le montage est
   effectif, l'utilisateur peut ou ne peut pas.
4. **La persistance après reboot**, dès que le sujet la justifie. C'est le piège
   qui fait échouer les candidats RHCSA : `setsebool` sans `-P`, un montage
   absent de `/etc/fstab`, un service non `enable`.

#### Le contrôle négatif est obligatoire

Un test qui passe sur une VM vierge ne prouve rien. Avant de déclarer un lab
terminé, vérifier les **deux** sens :

- **rouge** avant que l'apprenant ait travaillé (`LAB_NO_REPLAY=1`),
- **vert** après le rejeu de la solution officielle.

Un lab qui n'a pas passé ce double contrôle n'est pas terminé.

#### Valider les labs un par un

Ne jamais relancer la suite complète tant que chaque lab en erreur n'est pas
vert **unitairement** (`dsoxlab check <lab-id>`). Une suite globale masque les
causes, et une panne de harnais ressemble à une régression de contenu.

### 5. Portabilité

- **Aucun** chemin personnel dans un fichier livré. Ni
  `/home/bob/Projets/...`, ni `~/Projets/linux-training` (le dépôt a été
  renommé `linux-dsoxlab-training`). Un lab se joue depuis le dépôt courant.
- **Aucune IP en dur.** Les adresses sont dérivées par Terraform et exposées par
  l'inventaire dynamique de `dsoxlab`. Un test qui contient `10.10.30.11` casse
  au premier reprovisionnement.
- Les tests passent par les fixtures du `conftest.py` racine (`lab_host`,
  `lab_target_host`), jamais par un `ssh` codé à la main.

### 6. Le français d'abord, l'anglais ensuite

Le lecteur visé est francophone. On écrit `README.fr.md` et `scenario.fr.md`
d'abord, puis on traduit vers `README.md` et `scenario.md`. Les deux versions
doivent exister : `dsoxlab validate-structure` signale une parité rompue.

`lab.yaml` reste canonique **en anglais** (id, title, level, skills) ;
`lab.fr.yaml` ne surcharge que `title` et `description`. Les identifiants et
les noms de répertoires sont **toujours en anglais**.

---

## Le contrat réel d'un lab

### Arborescence, telle qu'elle est sur le disque

```text
labs/linux/<section>/<lab>/
├── lab.yaml              ← métadonnées canoniques (EN). REQUIS
├── lab.fr.yaml           ← surcharges FR : title + description uniquement
├── README.md             ← tutoriel guidé EN. REQUIS
├── README.fr.md          ← tutoriel guidé FR
├── scenario.md           ← contexte narratif EN. REQUIS
├── scenario.fr.md        ← contexte narratif FR
├── setup.yaml            ← REQUIS si runtime vm : prépare l'état de départ
├── cleanup.yaml          ← REQUIS si runtime vm : reset idempotent
├── fixtures/             ← si runtime shell : données copiées dans le workdir
└── challenge/
    ├── README.md         ← énoncé EN. REQUIS
    ├── README.fr.md      ← énoncé FR
    ├── hints.yaml        ← indices à coût croissant
    ├── work/             ← (runtime shell) répertoire de travail de l'apprenant
    └── tests/
        └── test_functional.py   ← REQUIS, **nom exact imposé**
```

Il n'y a **ni `runtime/`, ni `cleanup.sh`, ni `Makefile`, ni `evidence/`**.

### `lab.yaml`, champs réellement lus

```yaml
id: l2-swap-management                    # REQUIS, unique dans le dépôt
title: "Manage swap space"                # REQUIS, anglais
level: l2                                 # REQUIS
skills: [storage, swap]                   # REQUIS, non vide
distros: [alma10, ubuntu24]               # REQUIS, non vide
doc_url: https://www.stephane-robert.info/docs/...   # REQUIS, http(s)
lab_type: lab                             # lab | challenge | capstone
estimated_time: "25m"
certification_tags: [rhcsa, lfcs]
runtime:
  type: vm                                # vm | shell. PAS `kvm`, PAS `incus`
  targets:                                # REQUIS pour vm, non vide
    - name: rhel
      host: alma-rhcsa-1.lab              # doit exister dans meta.yml: infra.hosts[]
      label_fr: "AlmaLinux 10"
      roles:                              # multi-hôtes, optionnel
        server: alma-rhcsa-2.lab          # → groupe Ansible lab_server
  default: rhel
  snapshot_required: false
  # --- si type: shell ---
  workdir: challenge/work                 # REQUIS pour shell
  fixtures: [acces.log]                   # copiés à plat dans le workdir
validation:                               # DÉCLARATIF : dsoxlab ne s'en sert
  functional: true                        # jamais pour décider. Ce sont les
  security: false                         # tests qui prouvent.
  persistence_after_reboot: false
```

**`runtime.host` n'existe pas.** Ce champ, que l'ancienne version de ce fichier
donnait comme obligatoire, n'est lu nulle part : il est ignoré en silence. Le
FQDN vit dans `runtime.targets[].host`.

**`bloc` et `bloc_order` ne s'écrivent pas** : `dsoxlab` les dérive de la
position du lab dans `meta.yml: sections[].labs[]`. C'est de là que
`dsoxlab next` tire l'ordre pédagogique.

### Les pièges du contrat

1. **Un `lab.yaml` invalide disparaît en silence.** Une erreur de parsing donne
   un `logger.warning` que rien n'affiche, puis le lab est ignoré. Un lab absent
   de `dsoxlab list-labs` est presque toujours un `lab.yaml` qui lève.
   **D'où la règle : `dsoxlab list-labs` d'abord, `validate-structure` ensuite.**
2. **La découverte se fait par chemin, jamais par `id`.** Un lab existe si et
   seulement si `labs/**/lab.yaml` existe. Le `meta.yml` ne fait qu'ordonner et
   nommer les blocs.
3. **`validate-structure` ne vérifie pas qu'un lab listé dans `meta.yml` existe
   sur le disque.** Il itère sur ce qui a été chargé avec succès.
4. **Un host de `targets[]` absent de `meta.yml: infra.hosts[]`** ne se voit
   qu'au run, sur la machine de l'apprenant. `validate-structure` le rattrape
   désormais, mais seulement si le `meta.yml` est lisible.

---

## Topologie

Trois VM déclarées dans `meta.yml`, provisionnées par `dsoxlab provision` :

| Hôte | Distro | Rôle |
| --- | --- | --- |
| `alma-rhcsa-1.lab` | `alma10` | `rhcsa-primary`, cible par défaut |
| `alma-rhcsa-2.lab` | `alma10` | `rhcsa-secondary` (client/serveur : NFS, SSH, NBDE) |
| `ubuntu-lfcs-1.lab` | `ubuntu24` | `lfcs-debian`, sujets multi-distribution |

Réseau libvirt `lab-linux`, CIDR `10.10.30.0/24`. Providers candidats :
`kvm`, `incus`, `outscale` ; l'apprenant en choisit un avec
`dsoxlab use --provider kvm`.

> **Les IP ne se déclarent pas et ne se codent pas en dur.** Elles sont dérivées
> de la **position** de l'hôte dans `infra.hosts[]`. Conséquence directe : tout
> nouvel hôte s'ajoute **en fin de liste**, sinon les adresses de tous les
> suivants sont réattribuées et libvirt refuse le plan en cours de route.

### Les deux comptes, et lequel viser

Le cloud-init pose deux comptes sur chaque nœud, tous deux dans `wheel`/`sudo`
avec `sudo NOPASSWD:ALL` et clé SSH uniquement :

- **`ansible`** : compte de **service**. C'est **lui** que `dsoxlab` et les
  playbooks utilisent pour se connecter.
- **`student`** : compte **humain**, pour le debug.

**Tout lab qui restreint la connexion (`AllowUsers`, `remote_user`, durcissement
`sshd`) doit viser `ansible`.** Un lab qui verrouille sur `student` coupe
l'automatisation et casse sa propre validation. L'ancienne version de ce fichier
annonçait `student` comme compte de service : c'est faux.

### Groupes Ansible injectés à l'exécution

- `labenv` : tous les hôtes du `meta.yml`.
- `lab_target` : **le** host de la target résolue. Les playbooks des labs
  ciblent `hosts: lab_target`.
- `lab_<role>` : un par entrée de `roles`.

---

## Cycle de vie d'un lab

```bash
dsoxlab use linux --provider kvm     # contexte et provider
dsoxlab provision                    # crée les VM (Terraform packagé dans dsoxlab)
dsoxlab list-labs                    # le catalogue
dsoxlab run <lab-id>                 # setup.yaml puis session sur la cible
dsoxlab check <lab-id>               # joue les tests, calcule le score
dsoxlab hint <lab-id>                # indice, au prix de points
dsoxlab reset <lab-id>               # cleanup.yaml puis setup.yaml
dsoxlab destroy                      # libère tout
```

`dsoxlab check --target <name>` exporte `DSOXLAB_TARGET_HOST`, que le
`conftest.py` lit pour tester la distribution choisie. Sans lui, un lab
multi-distribution ne teste que son hôte par défaut.

---

## Écrire un lab

### Le scénario pose la situation, pas la procédure

`scenario.fr.md` tient en quelques lignes : la situation, ce qui est cassé ou
attendu, et pourquoi ça compte dans la vraie vie. Il ne donne aucune commande.

### `README.fr.md` : un tutoriel guidé, pas une présentation

**Ne pas confondre les deux fichiers Markdown du lab.** Les inverser est
l'erreur la plus fréquente :

| Fichier | Rôle | Ton |
| --- | --- | --- |
| `README.fr.md` (racine) | **Tutoriel guidé** : on apprend le mécanisme sur des exemples jetables | « voici `systemctl show` sur un cas simple, observez ce qu'il rend » |
| `challenge/README.fr.md` | **Énoncé** : le problème distinct à résoudre | « le service doit survivre au reboot » |

Un `README.fr.md` qui se contente d'annoncer ce que l'apprenant va faire a raté
sa cible : c'est un second énoncé, pas un tutoriel. Le lecteur doit pouvoir
**suivre le fichier commande par commande** et voir le mécanisme se comporter
sous ses yeux.

#### RÈGLE ABSOLUE : le tutoriel ne donne jamais la solution du challenge

Le tutoriel enseigne chaque mécanisme sur un exemple **jetable et neutre**. Le
challenge est un problème **différent**, que l'apprenant résout en transférant
ce qu'il a appris.

Les exemples du tutoriel portent des noms **volontairement étrangers** au sujet
du challenge : un service `demo-horloge`, un utilisateur `meteo`, un point de
montage `/srv/inventaire`. Jamais l'unité, l'utilisateur ni le chemin que le
challenge demande de produire.

**Contrôle mécanique, avant de livrer.** Les identifiants du tutoriel et ceux du
challenge ne doivent pas se recouper :

```bash
# noms de services, users, groupes, chemins cités de part et d'autre
grep -oE '\b[a-z][a-z0-9_.-]{3,}\.(service|timer|mount)\b' README.fr.md | sort -u
grep -oE '\b[a-z][a-z0-9_.-]{3,}\.(service|timer|mount)\b' challenge/README.fr.md | sort -u
```

Un recouvrement est le symptôme direct de l'erreur.

#### Où s'exécutent les exemples du tutoriel

Puisqu'ils sont jetables, ils ne touchent pas l'état que le challenge évalue :

- un répertoire temporaire (`mktemp -d`) pour tout ce qui est fichiers ;
- une unité systemd de démonstration au nom étranger, supprimée en fin de
  section ;
- pour un lab `shell`, **jamais** le `challenge/work/`, qui est le terrain du
  challenge et pas du cours.

### `challenge/README.fr.md` : l'énoncé

Il donne l'objectif et les contraintes **vérifiables**, pas la marche à suivre.
Il indique où travailler, et rappelle les deux commandes utiles :

```bash
dsoxlab check <lab-id>   # valide
dsoxlab hint  <lab-id>   # un indice, au prix de points
```

**Piège vécu, à ne pas reproduire** : un énoncé qui dit « édite le fichier avec
`nano` ou `vim` » alors qu'aucun lab antérieur n'a enseigné l'édition. Toute
compétence exigée par un challenge doit avoir été enseignée par un lab
**précédent** dans l'ordre du `meta.yml`, ou par le tutoriel du lab lui-même.

### `challenge/hints.yaml` : des indices, pas la correction

Coût croissant. Le premier oriente (« regarde du côté de la persistance »), le
dernier nomme la commande sans donner ses arguments. Aucun indice ne contient la
ligne à copier.

### Les tests : `challenge/tests/test_functional.py`

Nom **exact** imposé par le validator. Ils utilisent `pytest-testinfra` via les
fixtures du `conftest.py` racine :

```python
def test_le_service_survit_au_reboot(lab_host):
    host = lab_host("lab_target")
    assert host.service("chronyd").is_enabled
```

Ils prouvent l'état (règle 4), jamais le contenu d'un fichier quand un
interrogateur structuré existe.

---

## Les solutions de référence

Une solution par lab, **chiffrée**, sous `solution/linux/<section>/<lab>/` :

- **`solution.yaml`** pour un lab `vm` (playbook joué par `ansible-runner` sur
  la target). 64 labs.
- **`solution.sh`** pour un lab `shell` (script joué dans le workdir). 20 labs.

Le `conftest.py` racine porte une fixture autouse `_apply_lab_state` qui rejoue
la solution **avant** les tests, en la déchiffrant avec `.vault-pass`. C'est ce
qui permet de prouver qu'un lab est faisable.

**`LAB_NO_REPLAY=1` désactive ce rejeu**, et `dsoxlab check` le pose : l'apprenant
est donc bien évalué sur son propre travail. Les deux modes servent le double
contrôle de la règle 4 : sans la variable, on doit être **vert** ; avec elle sur
une VM fraîche, on doit être **rouge**.

Rejouer toutes les solutions d'un coup :

```bash
python3 scripts/verify-solutions.py            # rejoue tout, écrit verified-with.json
python3 scripts/verify-solutions.py --lab l1-first-terminal
python3 scripts/verify-solutions.py --check    # échoue si une solution casse
python3 scripts/verify-solutions.py --negative # + contrôle négatif (doit être rouge)
```

Une montée de version (noyau, systemd, distribution) peut casser une solution
sans que personne ne s'en aperçoive, parce que les tests d'un lab ne tournent
que si quelqu'un le joue.

### Lancer la suite : trois conditions, sinon le résultat ne veut rien dire

`scripts/verify-solutions.py` **est** le point d'entrée. Les trois conditions
ci-dessous ont chacune produit une avalanche d'erreurs qui accusait le contenu
alors que le harnais était en cause. Vécu le 2026-07-28 : `274 errors`, puis
`136 errors`, aucune imputable à un lab.

**1. Ne jamais lancer `pytest labs/` directement.** C'est l'erreur qui coûte le
plus cher. La fixture `_apply_lab_state` du `conftest.py` rejoue la
**solution**, mais **pas** le `setup.yaml` : elle ne pose donc pas l'état de
départ du lab. `verify-solutions.py`, lui, appelle **`dsoxlab reset`**
(`cleanup.yaml` puis `setup.yaml`) avant chaque lab, et c'est toute la
différence. Symptôme typique d'un `pytest labs/` : un `solution.yaml` qui
échoue sur un chemin que son propre `setup.yaml` était censé créer, du genre
`restorecon: lstat(/srv/labweb) failed: No such file or directory`.

**2. Résoudre le provider avant de lancer quoi que ce soit.** Le `meta.yml` de
ce dépôt déclare **trois** candidats (`kvm`, `incus`, `outscale`). Or une liste
n'est résolue d'office que si elle a **un seul** élément : sans sélection
explicite, **tous** les labs `vm` lèvent `ProviderUnresolved` au setup.

```bash
dsoxlab use --provider kvm     # persiste active_provider dans .dsoxlab-context.json
DSOXLAB_PROVIDER=kvm ...       # ou en one-shot, utile en shell non interactif
```

Un shell non interactif n'hérite pas de l'export du shell de travail : c'est la
raison pour laquelle « ça passait hier » et pas dans la session suivante.
Contrôle : `dsoxlab doctor` doit annoncer les **84 labs** détectés et un
provider actif.

**3. Partir de VM fraîches.** Les labs partagent `alma-rhcsa-1.lab`, et il n'y a
**aucune isolation** entre eux : un service laissé debout par un lab casse les
suivants. Cas vérifié : `l4-reverse-proxy-lb` laisse **HAProxy** sur le port
**80**, et les labs `httpd` qui suivent échouent alors sur
`(98)Address already in use: AH00072: make_sock: could not bind to address
0.0.0.0:80`, un symptôme qui ne dit rien de leur propre solution. Repartir d'une
**image vierge** (ou `dsoxlab destroy` puis `provision`) avant une campagne
complète, et diagnostiquer un service qui ne démarre pas par
`ss -ltnp | grep :80` sur la VM avant d'accuser le lab.

**Corollaire, et c'est la règle qui fait gagner du temps :** tant qu'un lab en
erreur n'est pas **vert unitairement** (`--lab <id>`), relancer la suite
complète ne mesure plus rien. Une série d'échecs simultanés sur des sujets
indépendants accuse le harnais, pas le contenu.

---

## Vérifications avant de rendre la main

```bash
dsoxlab list-labs                      # le lab apparaît (sinon lab.yaml lève)
dsoxlab validate-structure             # structure, métadonnées et contenu
dsoxlab check <lab-id>                 # les tests passent réellement
DSOXLAB_LANG=fr dsoxlab show <lab-id>  # la surcharge FR s'affiche
grep -c $'\u2014' <fichier>            # tiret cadratin : doit renvoyer 0
```

Et le double contrôle de la règle 4 : rouge avant travail, vert après solution.

### Le bon interpréteur pour `pytest`

**`pytest` n'est pas dans le python de base.** Un `python3 -m pytest` lancé avec
`/usr/bin/python3` échoue en silence, et l'échec **ne ressemble pas** à un
problème d'interpréteur : toutes les solutions sortent en échec d'un coup, on
croit à une régression de contenu alors que c'est le harnais.

**Une suite qui tombe en panne sur tous ses cas d'un seul coup, y compris ceux
qui passaient hier, accuse le harnais avant le sujet.**

En pratique, `dsoxlab check <lab-id>` embarque déjà le bon python : c'est la
voie la plus sûre. Les invocations directes ne servent qu'au double contrôle.

---

## Style de rédaction française

- **Accents complets, toujours**, majuscules comprises.
- **Jamais de tiret cadratin** (`U+2014`) ni de demi-cadratin (`U+2013`). Deux-points
  pour introduire, virgules ou parenthèses pour une incise, point ou
  point-virgule pour une rupture. Contrôle : `grep -c $'\u2014' <fichier>` doit
  renvoyer **0**.
- **Encadrés avec parcimonie** : ce qui mérite d'être lu mérite d'être dans le
  texte.
- Pas d'emoji décoratif dans les titres de sections.

---

## Pièges Linux, observés en production

### systemd

- `systemctl daemon-reload` oublié après modification d'une unité : systemd lit
  l'ancienne version et le lab échoue silencieusement.
- Préférer un drop-in `/etc/systemd/system/<svc>.d/override.conf` à l'édition de
  l'unité principale : l'apprenant apprend la bonne pratique.
- `systemctl enable --now` pour tout lab de persistance.

### SELinux

- **`setenforce 0` est interdit** dans la pédagogie. Un denial est une occasion
  d'apprendre `audit2allow`, `restorecon`, `semanage fcontext`, pas de contourner.
- `setsebool -P` : sans `-P`, la persistance après reboot est cassée.
- `chcon` est **temporaire** (perdu au prochain `restorecon`). Pour durer :
  `semanage fcontext -a -t <type> '<path>'` puis `restorecon -Rv <path>`.

### Réseau et pare-feu

- firewalld : `--permanent` **et** `--reload`, sinon la règle vaut pour la
  session ou pour le prochain boot, mais pas les deux.
- NetworkManager : `nmcli con reload` après avoir posé un fichier dans
  `/etc/NetworkManager/system-connections/`.

### Stockage

- xfs exige un device d'au moins 300 MiB (prévoir 800 MiB pour partitionner).
- LVM : `pvcreate`, puis `vgcreate`, puis `lvcreate`. L'ordre compte.
- `/etc/fstab` : valider avec `mount -a` **avant** le reboot. Une faute en fstab
  casse le boot.

### État partagé entre labs

Les labs partagent les mêmes VM : l'état est hérité d'un lab à l'autre.

- Le `cleanup.yaml` doit purger **tout** ce que la solution a posé : fichiers
  sous `/etc`, services activés, paquets, partitions, règles de pare-feu,
  contextes SELinux.
- Test à chaque livraison : enchaîner trois labs différents sur la même VM sans
  reprovisionner. Un test qui échoue accuse le `cleanup.yaml` du lab précédent.

---

## Commits

Format : `feat(<section>): <description>`, ou
`fix:` / `docs:` / `refactor:` / `chore:` / `test:` / `ci:`.

- `feat(l1): lab sur l'édition d'un fichier avant le premier challenge`
- `fix(l2): cleanup.yaml purge le montage laissé par la solution`

---

## La CLI est extérieure

Le moteur (`cli.py`, `runtimes/`, `discovery/`, `validators/`, `infra/`) vit dans
`~/Projets/dsoxlab/` et son propre `CLAUDE.md` fait foi pour le contrat. Ici, ce
qui pilote la CLI est déclaratif :

- `meta.yml` : identité du dépôt, infra, ordre des sections ;
- `lab.yaml` et `lab.fr.yaml` : métadonnées du lab ;
- `setup.yaml` et `cleanup.yaml` : préparation et reset côté VM ;
- `challenge/tests/test_functional.py` : la preuve ;
- `challenge/hints.yaml` : les indices.

Une évolution du contrat se fait dans `dsoxlab`, puis se répercute ici.
