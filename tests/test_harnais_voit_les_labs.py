"""Le harnais de rejeu voit-il chaque lab du catalogue ?

Ce fichier existe à cause d'une passe perdue, le 2026-10-16.

La fixture autouse `_apply_lab_state` du `conftest.py` racine déchiffre la
solution du formateur et l'applique avant les tests. Elle rend la main **sans
un mot** dans quatre cas, dont trois sont indiscernables d'un rejeu réussi
quand on ne regarde que le résultat des tests :

1. `LAB_NO_REPLAY=1` est posé (voulu : c'est ce que fait `dsoxlab check`) ;
2. `_find_lab_root` ne reconnaît pas la racine du lab ;
3. le `lab.yaml` annonce un runtime `shell` alors que la solution est un
   playbook, ou l'inverse ;
4. la solution n'est pas au chemin attendu.

Le cas 2 s'est produit sur l'ensemble du catalogue : le critère hérité du
catalogue Linux exigeait trois composants de chemin
(`labs/<categorie>/<section>/<lab>/`), là où les labs d'ici vivent à
`labs/<lab>/`. Les tests tournaient donc sur une machine où la solution
n'avait jamais été jouée, et les six échecs ressemblaient à un lab mal écrit.

**Une panne de harnais déguisée en défaut de contenu est la plus chère de
toutes** : on cherche la cause dans le sujet, qui est sain. Ce test la nomme en
une seconde, sans machine et sans infrastructure, et il couvre tous les labs à
venir.

Il ne prouve pas qu'une solution est juste : c'est le travail de
`scripts/verify-solutions.py --negative`, qui demande une VM. Il prouve que le
chemin du rejeu est branché, ce qui en est le préalable.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

RACINE = Path(__file__).resolve().parents[1]
LABS = RACINE / "labs"

if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import conftest  # noqa: E402


def labs_du_catalogue() -> list[Path]:
    return sorted(p.parent for p in LABS.rglob("lab.yaml"))


def identifiant(chemin: Path) -> str:
    return chemin.name


LABS_DU_CATALOGUE = labs_du_catalogue()


def test_le_catalogue_a_des_labs() -> None:
    """Sans ce contrôle, tous les suivants passeraient sur une liste vide.

    Un test paramétré sur une collection vide ne s'exécute jamais et compte
    pour un succès. C'est la panne qui mesure sa propre absence.
    """
    assert LABS_DU_CATALOGUE, (
        f"Aucun lab.yaml sous {LABS}. Les contrôles de ce fichier porteraient "
        "sur une liste vide et passeraient sans rien mesurer."
    )


@pytest.mark.parametrize("lab", LABS_DU_CATALOGUE, ids=identifiant)
def test_la_racine_du_lab_est_reconnue_depuis_ses_tests(lab: Path) -> None:
    """`_find_lab_root`, appelée comme la fixture l'appelle."""
    fichiers = sorted((lab / "challenge" / "tests").glob("test_*.py"))
    assert fichiers, (
        f"{lab.name} n'a aucun fichier de test sous challenge/tests/. "
        "`validate-structure` exige `test_functional.py`, au nom exact."
    )
    for fichier in fichiers:
        trouvee = conftest._find_lab_root(fichier.resolve())
        assert trouvee == lab, (
            f"Depuis {fichier.relative_to(RACINE)}, le harnais désigne "
            f"« {trouvee} » comme racine du lab au lieu de « {lab} ». "
            "La fixture `_apply_lab_state` rendrait la main sans un mot, et "
            "les tests tourneraient sur une machine où la solution n'a jamais "
            "été jouée."
        )


@pytest.mark.parametrize("lab", LABS_DU_CATALOGUE, ids=identifiant)
def test_le_runtime_lu_par_le_harnais_est_celui_du_lab(lab: Path) -> None:
    """Le harnais et le `lab.yaml` doivent dire la même chose.

    `_read_lab_runtime` est ce que la fixture interroge pour choisir entre le
    rejeu d'un playbook et celui d'un script. Un désaccord avec le `lab.yaml`
    envoie la solution par le mauvais chemin, et là encore en silence.
    """
    declare = yaml.safe_load((lab / "lab.yaml").read_text(encoding="utf-8"))
    runtime_declare = (declare.get("runtime") or {}).get("type", "shell")

    runtime_lu, hote_lu = conftest._read_lab_runtime(lab)

    assert runtime_lu == runtime_declare, (
        f"{lab.name} déclare runtime.type={runtime_declare!r} mais le harnais "
        f"lit {runtime_lu!r}. La solution serait rejouée par le mauvais chemin."
    )

    if runtime_declare in {"vm", "kvm", "incus"}:
        cibles = (declare.get("runtime") or {}).get("targets") or []
        hotes = {c.get("host") for c in cibles}
        assert hote_lu in hotes, (
            f"{lab.name} : le harnais retient l'hôte {hote_lu!r}, absent des "
            f"runtime.targets[].host du lab ({sorted(h for h in hotes if h)}). "
            "La solution se jouerait sur une autre machine que les tests."
        )


@pytest.mark.parametrize("lab", LABS_DU_CATALOGUE, ids=identifiant)
def test_la_solution_est_au_chemin_que_le_harnais_interroge(lab: Path) -> None:
    """Le chemin de la solution, calculé comme la fixture le calcule.

    Une solution présente mais rangée ailleurs que là où la fixture la cherche
    est une solution absente, et l'absence est traitée en silence : « les tests
    tournent sur l'état actuel ». Sur un lab non fait, cela veut dire zéro.
    """
    declare = yaml.safe_load((lab / "lab.yaml").read_text(encoding="utf-8"))
    runtime = (declare.get("runtime") or {}).get("type", "shell")
    relatif = lab.relative_to(LABS)

    attendu = "solution.sh" if runtime == "shell" else "solution.yaml"
    chemin = RACINE / "solution" / relatif / attendu

    assert chemin.is_file(), (
        f"{lab.name} est un lab {runtime!r}, donc le harnais cherche sa "
        f"solution à {chemin.relative_to(RACINE)}, qui n'existe pas. "
        "La fixture rendrait la main sans un mot et les tests mesureraient "
        "une machine où rien n'a été fait."
    )
