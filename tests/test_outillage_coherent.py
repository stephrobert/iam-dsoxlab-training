"""Chaque vérificateur est câblé, et chaque hook pointe un test réel.

LE GARDE-FOU DU GARDE-FOU, ET IL A UNE HISTOIRE

Repris du catalogue devsecops, qui l'a écrit après avoir trouvé neuf
vérificateurs dans `tests/` et un seul câblé à un hook. Les huit autres ne
tournaient que si quelqu'un lançait `pytest tests/` à la main, c'est-à-dire
jamais pendant un commit.

C'est pire que de ne pas les avoir. Un vérificateur qu'on croit en poste
dispense de regarder, et le défaut qu'il devait attraper passe avec la
tranquillité de celui qui pense être couvert.

Le contrôle va dans les deux sens, parce que les deux dérives existent :

- un test écrit et jamais câblé ne protège rien ;
- un hook qui pointe un test absent échoue à chaque commit, et le réflexe est
  alors de désactiver le hook, donc d'en perdre un vrai.

Un test peut légitimement ne pas être câblé, par exemple parce qu'il demande
une machine provisionnée. Il est alors recensé dans `NON_CABLES`, AVEC SA
RAISON. La liste est courte à dessein : elle se lit, et une raison vague se
remarque.

    pytest tests/test_outillage_coherent.py -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RACINE = Path(__file__).resolve().parent.parent
TESTS = RACINE / "tests"
CONFIGURATION = RACINE / ".pre-commit-config.yaml"

#: Les tests que l'on n'attend PAS dans un hook, et pourquoi.
#:
#: Rien ici pour l'instant : les trois vérificateurs du dépôt tournent sans
#: machine et sont tous câblés. Le jour où un test exigera une infrastructure
#: provisionnée, il viendra ici avec sa raison, et non en silence.
NON_CABLES: dict[str, str] = {}


def lister_les_verificateurs() -> list[str]:
    """Les fichiers de vérification du dépôt.

    Le nom ne commence pas par `test` à dessein : pytest ramasserait la
    fonction comme un test et avertirait à chaque passage, et un
    avertissement qu'on apprend à ignorer finit par cacher un vrai.
    """
    return sorted(p.name for p in TESTS.glob("test_*.py"))


def hooks_locaux() -> list[dict]:
    donnees = yaml.safe_load(CONFIGURATION.read_text(encoding="utf-8"))
    locaux = []
    for depot in donnees.get("repos", []):
        if depot.get("repo") == "local":
            locaux.extend(depot.get("hooks", []))
    return locaux


def verificateurs_cites_par_les_hooks() -> dict[str, str]:
    """Les fichiers de test que les hooks lancent, et par quel hook."""
    cites = {}
    for hook in hooks_locaux():
        for nom in re.findall(r"tests/(test_\w+\.py)", hook.get("entry", "")):
            cites[nom] = hook.get("id", "(sans id)")
    return cites


def test_la_configuration_pre_commit_existe() -> None:
    """Sans elle, tous les contrôles de ce fichier porteraient sur du vide.

    Et son absence serait elle-même le défaut : un catalogue sans pre-commit
    accepte un secret au premier commit distrait.
    """
    assert CONFIGURATION.is_file(), (
        f"{CONFIGURATION.name} est absent. Les huit autres catalogues en ont "
        "un, et c'est lui qui arrête un secret ou une solution en clair avant "
        "que git ne la garde pour toujours."
    )


def test_il_y_a_des_verificateurs_a_controler() -> None:
    assert lister_les_verificateurs(), (
        f"Aucun test_*.py sous {TESTS}. Les contrôles de ce fichier porteraient "
        "sur une liste vide et passeraient sans rien mesurer."
    )


@pytest.mark.parametrize("fichier", lister_les_verificateurs())
def test_chaque_verificateur_est_cable_ou_recense(fichier: str) -> None:
    """Un test écrit et jamais lancé ne protège rien.

    Ce fichier-ci est évidemment exempté : il contrôle le câblage, il n'a pas
    à se contrôler lui-même pour exister.
    """
    if fichier == Path(__file__).name:
        return

    cites = verificateurs_cites_par_les_hooks()
    if fichier in cites:
        return

    raison = NON_CABLES.get(fichier)
    assert raison, (
        f"tests/{fichier} n'est câblé à aucun hook de {CONFIGURATION.name} et "
        "n'est pas recensé dans NON_CABLES. Il ne tournera donc que si "
        "quelqu'un lance pytest à la main, c'est-à-dire jamais pendant un "
        "commit. Câblez-le, ou recensez-le avec sa raison."
    )
    assert len(raison) > 20, (
        f"tests/{fichier} est recensé dans NON_CABLES avec une raison trop "
        f"courte pour en être une : {raison!r}. Une raison vague laisse passer "
        "le vérificateur suivant."
    )


@pytest.mark.parametrize("fichier", sorted(verificateurs_cites_par_les_hooks()))
def test_chaque_hook_pointe_un_test_qui_existe(fichier: str) -> None:
    """Un hook qui pointe un test absent échoue à chaque commit.

    Et le réflexe devient alors de passer outre, ce qui fait perdre les hooks
    qui marchaient.
    """
    hook = verificateurs_cites_par_les_hooks()[fichier]
    assert (TESTS / fichier).is_file(), (
        f"Le hook « {hook} » lance tests/{fichier}, qui n'existe pas. Chaque "
        "commit échouerait, et la tentation serait de désactiver le hook."
    )


def test_aucun_test_recense_n_est_en_fait_cable() -> None:
    """La liste des exceptions doit rester juste, sinon elle devient du décor."""
    cites = verificateurs_cites_par_les_hooks()
    doublons = sorted(set(NON_CABLES) & set(cites))
    assert not doublons, (
        f"Ces tests sont recensés comme non câblés alors qu'un hook les lance : "
        f"{doublons}. Retirez-les de NON_CABLES, sinon la liste ne dit plus la "
        "vérité et on cessera de la croire."
    )


def test_aucun_test_recense_n_a_disparu() -> None:
    """Un recensement qui survit au fichier qu'il décrit est un mensonge."""
    fantomes = sorted(nom for nom in NON_CABLES if not (TESTS / nom).is_file())
    assert not fantomes, (
        f"Ces tests sont recensés dans NON_CABLES mais n'existent plus : "
        f"{fantomes}."
    )
