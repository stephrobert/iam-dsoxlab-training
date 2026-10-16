"""Une sauvegarde qui se restaure, une montée qui n'a rien perdu, et une trace
qui est toujours là.

CINQ FAITS MESURÉS LE 2026-10-16 QUI DÉCIDENT DE CES TESTS

1. `kc.sh export` lancé DANS le conteneur en marche sort en **1**, sur
   « Unable to start the management interface on 0.0.0.0:9000: Address already
   in use », ET ÉCRIT QUAND MÊME LES FICHIERS. Un script qui lit le code de
   retour conclut à l'échec, un script qui liste le répertoire conclut au
   succès, et les deux se trompent sur ce qui compte, qui est le contenu.
   Lancé dans un conteneur éphémère (`docker compose run --rm --no-deps`), il
   sort en 0.

2. `<realm>-realm.json` ne contient AUCUN utilisateur : `has("users")` y vaut
   `false`. Les comptes sont dans un fichier séparé, `<realm>-users-0.json`.
   Qui sauvegarde le premier fichier croit avoir tout et a perdu tous les
   comptes.

3. Le fichier des comptes, lui, porte les `credentials` avec leur
   `secretData` : c'est un fichier de secrets, qui se protège comme tel.

4. L'export ne porte AUCUN événement. Les seules clefs qui parlent
   d'événements sont des clefs de configuration (`eventsEnabled`,
   `enabledEventTypes`...), pas les événements eux-mêmes. La trace de qui s'est
   connecté vit dans la base, dans `event_entity` et `admin_event_entity`, et
   nulle part dans un export.

5. La montée 26.7.5 vers 26.8.1 migre le schéma au démarrage et le DIT :
   « Updating database. Using changelog », puis « Migrating older model to
   26.8.0 ». Les cinq comptes, les deux clients et les événements survivent, et
   un compte se connecte encore.
"""

from __future__ import annotations

import json
import shlex

import pytest

from conftest import lab_host, lab_target_host, message

# L'hôte RÉELLEMENT testé. `dsoxlab check --target` peut en imposer un autre,
# et coder le nom en dur ferait tester la cible par défaut en prétendant tester
# celle qu'on a demandée.
CIBLE = lab_target_host("idp.lab")

IDENTIFIANTS = "/opt/iam-lab/identifiants-lab.txt"

#: Les tables qui portent la trace d'audit. Un export n'en contient rien.
TABLES_DE_TRACE = ("event_entity", "admin_event_entity")


@pytest.fixture(scope="module")
def idp():
    """La machine du lab.

    `lab_host` est une fonction du conftest, pas une fixture : chaque lab bâtit
    la sienne, ce qui permet à un lab multi-hôtes d'en avoir plusieurs.
    """
    return lab_host(CIBLE)


# ── Outils de lecture de l'état ──────────────────────────────────────────────


def _identifiants(hote) -> dict[str, str]:
    fichier = hote.file(IDENTIFIANTS)
    assert fichier.exists, message(
        en=f"{IDENTIFIANTS} is missing. The lab's setup did not run, or its "
        "staging script failed: the trace is in "
        "/var/log/dsoxlab-prepare.log on the machine.",
        fr=f"{IDENTIFIANTS} est absent. Le setup du lab n'a pas tourné, ou son "
        "script de mise en situation a échoué : la trace est dans "
        "/var/log/dsoxlab-prepare.log sur la machine.",
    )
    valeurs = {}
    for ligne in fichier.content_string.splitlines():
        if "=" in ligne and not ligne.startswith("#"):
            clef, _, valeur = ligne.partition("=")
            valeurs[clef.strip()] = valeur.strip()
    return valeurs


def _env_prod(hote, ids: dict[str, str]) -> dict[str, str]:
    """Le fichier d'environnement de l'instance, qui porte l'image épinglée."""
    fichier = hote.file(ids["ENV_PROD"])
    assert fichier.exists, message(
        en=f"{ids['ENV_PROD']} is missing.",
        fr=f"{ids['ENV_PROD']} est absent.",
    )
    valeurs = {}
    for ligne in fichier.content_string.splitlines():
        if "=" in ligne and not ligne.startswith("#"):
            clef, _, valeur = ligne.partition("=")
            valeurs[clef.strip()] = valeur.strip()
    return valeurs


def _jeton_admin(hote, ids: dict[str, str]) -> str:
    env = _env_prod(hote, ids)
    res = hote.run(
        f"curl -sS --max-time 20 -X POST "
        f"{ids['URL_PROD']}/realms/master/protocol/openid-connect/token "
        f"-d grant_type=password -d client_id=admin-cli "
        f"-d username={shlex.quote(env['KC_ADMIN'])} "
        f"-d password={shlex.quote(env['KC_ADMIN_PASSWORD'])}")
    try:
        return json.loads(res.stdout).get("access_token", "")
    except json.JSONDecodeError:
        pytest.fail(
            message(
            en="The production instance returned no administration "
            f"token: {res.stdout[:200]!r}",
            fr="L'instance de production n'a pas rendu de jeton "
            f"d'administration : {res.stdout[:200]!r}",
        ))


def _api(hote, ids: dict[str, str], jeton: str, chemin: str):
    res = hote.run(
        f"curl -sS --max-time 30 {ids['URL_PROD']}/admin/{chemin} "
        f"-H {shlex.quote('Authorization: Bearer ' + jeton)}")
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        pytest.fail(message(
            en=f"/admin/{chemin} returned no JSON: "
                    f"{res.stdout[:200]!r}",
            fr=f"/admin/{chemin} n'a pas rendu de JSON : "
                    f"{res.stdout[:200]!r}",
        ))


def _exiger_la_montee(hote, ids: dict[str, str]) -> None:
    """Refuse de conclure quoi que ce soit si la montée n'a pas eu lieu.

    Les trois contrôles de préservation qui suivent n'ont de sens qu'APRÈS la
    montée : avant, ils constatent que des comptes posés par le setup sont
    encore là, ce qui ne mesure rien et donnerait un lab à moitié vert avant
    d'avoir commencé.
    """
    jeton = _jeton_admin(hote, ids)
    infos = _api(hote, ids, jeton, "serverinfo")
    version = infos.get("systemInfo", {}).get("version", "")
    assert version == ids["VERSION_CIBLE"], message(
        en=f"The instance runs in \"{version}\" and not in "
        f"\"{ids['VERSION_CIBLE']}\": the upgrade did not happen, and finding "
        "the data intact therefore proves nothing.",
        fr=f"L'instance tourne en « {version} » et non en "
        f"« {ids['VERSION_CIBLE']} » : la montée n'a pas eu lieu, et "
        "constater que les données sont intactes ne prouve donc rien.",
    )


def _psql(hote, ids: dict[str, str], base: str, requete: str) -> str:
    """Une requête dans la base, lue en valeur brute."""
    return hote.run(
        f"docker exec {ids['CONTENEUR_BASE']} psql -U keycloak -d {base} "
        f"-tAc {shlex.quote(requete)}").stdout.strip()


# ── 1. La montée a eu lieu ──────────────────────────────────────────────────


def test_l_instance_tourne_dans_la_version_cible(idp):
    """La version est celle visée, et elle est épinglée dans le fichier lu.

    On regarde ce que le SERVEUR annonce, et non ce que le fichier déclare :
    une image changée dans le `.env` sans relance laisserait l'ancienne version
    en service, et le fichier dirait le contraire.
    """
    ids = _identifiants(idp)
    jeton = _jeton_admin(idp, ids)
    infos = _api(idp, ids, jeton, "serverinfo")
    version = infos.get("systemInfo", {}).get("version", "")

    assert version == ids["VERSION_CIBLE"], message(
        en=f"The instance announces version \"{version}\" and not "
        f"\"{ids['VERSION_CIBLE'] }\". Was the pinned image changed "
        f"in {ids['ENV_PROD']}, and the service restarted?",
        fr=f"L'instance annonce la version « {version} » et non "
        f"« {ids['VERSION_CIBLE'] }». L'image épinglée a-t-elle été changée "
        f"dans {ids['ENV_PROD']}, et le service relancé ?",
    )

    env = _env_prod(idp, ids)
    assert ids["VERSION_CIBLE"] in env.get("IMAGE_KEYCLOAK", ""), message(
        en="The server runs in the right version but the environment file "
        "does not refer to it: "
        f"IMAGE_KEYCLOAK = {env.get('IMAGE_KEYCLOAK', '(missing)')!r}. On "
        "the next restart, the old version would come back.",
        fr="Le serveur tourne dans la bonne version mais le fichier "
        f"d'environnement n'y fait pas référence : "
        f"IMAGE_KEYCLOAK = {env.get('IMAGE_KEYCLOAK', '(absent)')!r}. Au "
        "prochain redémarrage, l'ancienne version reviendrait.",
    )
    assert "@sha256:" in env.get("IMAGE_KEYCLOAK", ""), message(
        en="The image is not pinned by digest: "
        f"{env.get('IMAGE_KEYCLOAK')!r}. A tag moves, and two restarts can "
        "then give two versions.",
        fr="L'image n'est pas épinglée par digest : "
        f"{env.get('IMAGE_KEYCLOAK')!r}. Une étiquette se déplace, et deux "
        "redémarrages peuvent alors donner deux versions.",
    )


def test_la_base_porte_la_marque_de_la_migration(idp):
    """Le schéma a été migré, et la base est celle d'avant, non une neuve.

    C'est la différence entre une montée et une réinstallation : la seconde
    donnerait aussi la bonne version, sur des données qui ne sont plus les
    mêmes.
    """
    ids = _identifiants(idp)
    journaux = idp.run(
        f"docker logs {ids['CONTENEUR_KEYCLOAK']} 2>&1 "
        "| grep -iE 'Migrating older model|Updating database' | head -3")
    assert journaux.stdout.strip(), message(
        en="The instance's logs carry no trace of a schema migration. Either "
        "the upgrade did not happen, or the database was recreated empty, "
        "which is not an upgrade.",
        fr="Les journaux de l'instance ne portent aucune trace de migration de "
        "schéma. Soit la montée n'a pas eu lieu, soit la base a été recréée "
        "vide, ce qui n'est pas une montée.",
    )


# ── 2. La sauvegarde, et ce qu'elle vaut vraiment ───────────────────────────


def test_une_sauvegarde_de_la_base_existe_et_precede_la_montee(idp):
    """Une sauvegarde postérieure à la montée ne protège de rien.

    C'est le cas d'échec le plus courant, et le plus confortable : on sauvegarde
    après, tout va bien, et la sauvegarde ne décrit pas l'état qu'il aurait
    fallu pouvoir retrouver.
    """
    ids = _identifiants(idp)
    trouvees = idp.run(
        f"find {ids['REPERTOIRE_SAUVEGARDES']} -type f "
        r"\( -name '*.dump' -o -name '*.sql' -o -name '*.sql.gz' "
        r"-o -name '*.custom' \) -printf '%T@ %s %p\n' | sort -n")
    lignes = [l for l in trouvees.stdout.splitlines() if l.strip()]
    assert lignes, message(
        en=f"No backup in {ids['REPERTOIRE_SAUVEGARDES']}. The test looks there "
        "for a .dump, .sql, .sql.gz or .custom file.",
        fr=f"Aucune sauvegarde dans {ids['REPERTOIRE_SAUVEGARDES']}. Le test y "
        "cherche un fichier .dump, .sql, .sql.gz ou .custom.",
    )

    horodatage, taille, chemin = lignes[-1].split(None, 2)
    assert int(taille) > 10000, message(
        en=f"The backup {chemin} weighs only {taille} bytes. A Keycloak database "
        "with a realm and accounts runs to a few hundred kilobytes: this "
        "file is probably empty or truncated.",
        fr=f"La sauvegarde {chemin} ne pèse que {taille} octets. Une base de "
        "Keycloak avec un realm et des comptes en fait quelques centaines de "
        "kilo-octets : ce fichier est probablement vide ou tronqué.",
    )

    # La date de CRÉATION du conteneur, et non son dernier démarrage : un
    # simple redémarrage ne doit pas faire échouer un travail bien fait, alors
    # qu'un changement d'image recrée le conteneur.
    cree = idp.run(
        f"docker inspect -f '{{{{.Created}}}}' {ids['CONTENEUR_KEYCLOAK']} "
        "| xargs -I{} date -d {} +%s")
    assert cree.rc == 0 and cree.stdout.strip(), message(
        en=f"The creation date of {ids['CONTENEUR_KEYCLOAK']} cannot be read: "
        f"{cree.stderr[:200]!r}",
        fr=f"Impossible de lire la date de création de "
        f"{ids['CONTENEUR_KEYCLOAK']} : {cree.stderr[:200]!r}",
    )
    assert float(horodatage) < float(cree.stdout.strip()), message(
        en=f"The backup {chemin} is LATER than the creation of the target "
        "version's container. It was therefore taken after the upgrade, and it "
        "does not allow going back to the state before. A backup that does not "
        "precede the risky gesture protects nothing.",
        fr=f"La sauvegarde {chemin} est POSTÉRIEURE à la création du conteneur "
        "de la version cible. Elle a donc été prise après la montée, et elle "
        "ne permet pas de revenir à l'état d'avant. Une sauvegarde qui ne "
        "précède pas le geste risqué ne protège de rien.",
    )


def test_la_sauvegarde_se_restaure_dans_une_base_vide(idp):
    """Une sauvegarde qu'on n'a pas restaurée n'est pas une sauvegarde.

    Ce test ne lit pas le fichier : il le RESTAURE dans une base créée pour
    l'occasion, compte les comptes dedans, et la supprime. C'est le seul
    contrôle qui vaut, et c'est aussi le geste que personne ne fait avant d'en
    avoir besoin.
    """
    ids = _identifiants(idp)
    base = "essai_restauration_lab09"

    trouvees = idp.run(
        f"find {ids['REPERTOIRE_SAUVEGARDES']} -type f "
        r"\( -name '*.dump' -o -name '*.sql' -o -name '*.sql.gz' "
        r"-o -name '*.custom' \) -printf '%T@ %p\n' | sort -n | tail -1")
    assert trouvees.stdout.strip(), message(
        en="No backup to restore.",
        fr="Aucune sauvegarde à restaurer.",
    )
    chemin = trouvees.stdout.split(None, 1)[1].strip()

    idp.run(f"docker exec {ids['CONTENEUR_BASE']} psql -U keycloak -d postgres "
            f"-c 'DROP DATABASE IF EXISTS {base}'")
    creation = idp.run(
        f"docker exec {ids['CONTENEUR_BASE']} psql -U keycloak -d postgres "
        f"-c 'CREATE DATABASE {base}'")
    assert creation.rc == 0, message(
        en=f"The trial database cannot be created: {creation.stderr[:200]!r}",
        fr=f"Impossible de créer la base d'essai : {creation.stderr[:200]!r}",
    )

    try:
        if chemin.endswith(".sql.gz"):
            commande = (f"gunzip -c {shlex.quote(chemin)} | docker exec -i "
                        f"{ids['CONTENEUR_BASE']} psql -U keycloak -d {base}")
        elif chemin.endswith(".sql"):
            commande = (f"docker exec -i {ids['CONTENEUR_BASE']} psql "
                        f"-U keycloak -d {base} < {shlex.quote(chemin)}")
        else:
            commande = (f"docker exec -i {ids['CONTENEUR_BASE']} pg_restore "
                        f"-U keycloak -d {base} < {shlex.quote(chemin)}")
        restauration = idp.run(commande)

        tables = _psql(idp, ids, base,
                       "select count(*) from information_schema.tables "
                       "where table_schema='public'")
        assert tables.isdigit() and int(tables) > 50, message(
            en=f"Restoring {chemin} produced only {tables!r} tables. "
            f"Output: {restauration.stdout[-300:]!r} "
            f"{restauration.stderr[-300:]!r}",
            fr=f"La restauration de {chemin} n'a produit que {tables!r} tables. "
            f"Sortie : {restauration.stdout[-300:]!r} "
            f"{restauration.stderr[-300:]!r}",
        )

        comptes = _psql(
            idp, ids, base,
            "select count(*) from user_entity where realm_id in "
            f"(select id from realm where name='{ids['REALM']}')")
        attendus = int(ids["NB_COMPTES_ATTENDUS"])
        assert comptes.isdigit() and int(comptes) >= attendus, message(
            en=f"The restored database carries only {comptes!r} accounts of the realm "
            f"\"{ids['REALM']}\", instead of {attendus}. Was the backup taken "
            "on the right database, and with the data?",
            fr=f"La base restaurée ne porte que {comptes!r} comptes du realm "
            f"« {ids['REALM']} », au lieu de {attendus}. La sauvegarde a-t-elle "
            "été prise sur la bonne base, et avec les données ?",
        )
    finally:
        # La base d'essai part, quoi qu'il arrive : un test qui laisse des
        # traces fait échouer le suivant pour une raison qui n'est pas la
        # sienne.
        idp.run(f"docker exec {ids['CONTENEUR_BASE']} psql -U keycloak "
                f"-d postgres -c 'DROP DATABASE IF EXISTS {base}'")


def test_l_export_du_realm_existe_et_porte_les_comptes(idp):
    """Un export de realm se fait en DEUX fichiers, et l'un suffit rarement.

    Le fichier qu'on copie spontanément, `<realm>-realm.json`, ne contient
    aucun compte. Ce test exige donc que les comptes soient quelque part dans
    l'export.
    """
    ids = _identifiants(idp)
    fichiers = idp.run(
        f"find {ids['REPERTOIRE_EXPORTS']} -type f -name '*.json' "
        r"-printf '%p\n'")
    chemins = [l for l in fichiers.stdout.splitlines() if l.strip()]
    assert chemins, message(
        en=f"No JSON export in {ids['REPERTOIRE_EXPORTS']}.",
        fr=f"Aucun export JSON dans {ids['REPERTOIRE_EXPORTS']}.",
    )

    realm_trouve = False
    comptes_trouves = 0
    for chemin in chemins:
        brut = idp.file(chemin).content_string
        try:
            charge = json.loads(brut)
        except json.JSONDecodeError:
            pytest.fail(message(
                en=f"{chemin} is not readable JSON.",
                fr=f"{chemin} n'est pas du JSON lisible.",
            ))
        if isinstance(charge, dict) and charge.get("realm") == ids["REALM"]:
            realm_trouve = True
        utilisateurs = charge.get("users") if isinstance(charge, dict) else None
        if isinstance(utilisateurs, list):
            comptes_trouves += len(utilisateurs)

    assert realm_trouve, message(
        en=f"None of the exported files describes the realm \"{ids['REALM']}\": "
        f"{chemins}",
        fr=f"Aucun des fichiers exportés ne décrit le realm « {ids['REALM']} » : "
        f"{chemins}",
    )
    attendus = int(ids["NB_COMPTES_ATTENDUS"])
    assert comptes_trouves >= attendus, message(
        en=f"The export carries only {comptes_trouves} accounts instead of "
        f"{attendus}. The file \"{ids['REALM']}-realm.json\" contains NONE of "
        "them: the accounts are in a separate file, and that is precisely "
        "what one forgets to copy.",
        fr=f"L'export ne porte que {comptes_trouves} comptes au lieu de "
        f"{attendus}. Le fichier « {ids['REALM']}-realm.json » n'en contient "
        "AUCUN : les comptes sont dans un fichier séparé, et c'est précisément "
        "ce qu'on oublie de copier.",
    )


# ── 3. Rien n'a été perdu ───────────────────────────────────────────────────


def test_le_realm_ses_comptes_et_ses_clients_ont_survecu(idp):
    """Les comptages d'avant et d'après, sur le serveur qui tourne."""
    ids = _identifiants(idp)
    _exiger_la_montee(idp, ids)
    jeton = _jeton_admin(idp, ids)

    comptes = _api(idp, ids, jeton, f"realms/{ids['REALM']}/users?max=200")
    attendus = int(ids["NB_COMPTES_ATTENDUS"])
    assert len(comptes) >= attendus, message(
        en=f"The realm carries only {len(comptes)} accounts instead of {attendus}.",
        fr=f"Le realm ne porte que {len(comptes)} comptes au lieu de {attendus}.",
    )

    clients = _api(idp, ids, jeton, f"realms/{ids['REALM']}/clients")
    les_notres = [c for c in clients if c.get("clientId", "").startswith("appli")]
    assert len(les_notres) >= 2, message(
        en=f"The realm's application clients have disappeared: "
        f"{[c.get('clientId') for c in clients]}",
        fr=f"Les clients applicatifs du realm ont disparu : "
        f"{[c.get('clientId') for c in clients]}",
    )


def test_la_trace_d_audit_a_survecu(idp):
    """La preuve que la base a été MIGRÉE et non reconstruite depuis l'export.

    Un export de realm ne porte aucun événement. Si l'instance avait été
    remontée depuis l'export sur une base vide, la version serait juste, les
    comptes seraient là, et la trace de qui s'est connecté aurait disparu sans
    que rien ne le signale.
    """
    ids = _identifiants(idp)
    _exiger_la_montee(idp, ids)
    total = 0
    for table in TABLES_DE_TRACE:
        valeur = _psql(idp, ids, "keycloak", f"select count(*) from {table}")
        assert valeur.isdigit(), message(
            en=f"The table {table} could not be read: {valeur!r}. Is the instance's "
            "database the one from before the upgrade?",
            fr=f"La table {table} n'a pas pu être lue : {valeur!r}. La base de "
            "l'instance est-elle celle d'avant la montée ?",
        )
        total += int(valeur)
    assert total > 0, message(
        en="No event in the database after the upgrade, although the setup had "
        "recorded some. The database was recreated, or emptied: the version "
        "would be right and the audit trail would be gone.",
        fr="Aucun événement dans la base après la montée, alors que le setup en "
        "avait enregistré. La base a été recréée, ou vidée : la version serait "
        "juste et la trace d'audit aurait disparu.",
    )


def test_un_compte_se_connecte_apres_la_montee(idp):
    """Le seul contrôle qui compte pour les gens : ils rentrent encore.

    Les comptages peuvent être bons avec des justificatifs perdus : les
    `credentials` sont dans une autre table que les comptes.
    """
    ids = _identifiants(idp)
    _exiger_la_montee(idp, ids)
    res = idp.run(
        f"curl -sS --max-time 20 -X POST "
        f"{ids['URL_PROD']}/realms/{ids['REALM']}/protocol/openid-connect/token "
        f"-d grant_type=password -d client_id=appli-publique "
        f"-d username=compte1 -d password={shlex.quote(ids['MOT_DE_PASSE'])}")
    try:
        charge = json.loads(res.stdout)
    except json.JSONDecodeError:
        pytest.fail(message(
            en=f"The token endpoint did not answer in JSON: "
                    f"{res.stdout[:200]!r}",
            fr=f"Le point de jeton n'a pas répondu en JSON : "
                    f"{res.stdout[:200]!r}",
        ))
    assert "access_token" in charge, message(
        en="\"compte1\" can no longer log in after the upgrade: "
        f"{json.dumps(charge)[:250]}",
        fr="« compte1 » ne se connecte plus après la montée : "
        f"{json.dumps(charge)[:250]}",
    )
