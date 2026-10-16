"""Ce que l'apprenant lit ne porte ni emoji décoratif ni tiret cadratin.

Une règle de rédaction sans contrôle dérive au premier lab écrit vite. Celle-ci
est tenue ici, sur tous les fichiers que l'apprenant ouvre.

Le tiret cadratin mérite une explication, parce qu'il a l'air inoffensif. Il
arrive tout seul : un assistant en produit par habitude, un copier-coller depuis
une page anglaise en amène, et il se distingue mal d'un tiret ordinaire à la
relecture. Il n'appartient pas à la typographie de ce dépôt.

AUCUNE DETTE RECENSÉE ICI, ET C'EST LE MOMENT DE LE TENIR

Le catalogue devsecops, d'où ce contrôle est repris, a dû recenser 33 fichiers
déjà écrits : un cadratin se remplace par une virgule, un deux-points ou rien
selon la phrase, et une substitution en masse abîme le texte. Ce catalogue
commence avec zéro fichier fautif. La règle y est donc stricte et sans liste
d'exceptions, ce qui n'est possible qu'au début.

Les emoji sont refusés PARTOUT, y compris dans les énoncés. Le catalogue
devsecops les tolère dans ses briefs parce que 174 fichiers en portent déjà,
héritage de son gabarit. Ici, aucun.

Les flèches ne sont pas surveillées : `←` et `→` portent un sens dans un
tableau, là où un pictogramme n'en a pas.

    pytest tests/test_style_apprenant.py -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
LABS = RACINE / "labs"

#: Plages Unicode des pictogrammes décoratifs. Les flèches (0x2190-0x21FF) en
#: sont volontairement absentes.
PLAGES_EMOJI = [
    (0x1F300, 0x1FAFF),
    (0x2600, 0x27BF),
    (0xFE0F, 0xFE0F),
    (0x2B00, 0x2BFF),
]
EMOJI = re.compile("[" + "".join(f"{chr(a)}-{chr(b)}" for a, b in PLAGES_EMOJI) + "]")

CADRATIN = chr(0x2014)


def documents_lus_par_l_apprenant() -> list[Path]:
    """Les Markdown des labs, et la documentation de la racine.

    `preparation/` en est exclu : ce sont les notes de cadrage et les scripts
    réellement joués par les auteurs des leçons, conservés tels quels comme
    pièce à conviction. Les reformater leur retirerait leur valeur de
    témoignage, et aucun apprenant ne les ouvre.
    """
    trouves = sorted(LABS.rglob("*.md")) if LABS.is_dir() else []
    trouves += sorted(p for p in RACINE.glob("*.md"))
    return trouves


DOCUMENTS = documents_lus_par_l_apprenant()


def identifiant(chemin: Path) -> str:
    return str(chemin.relative_to(RACINE))


def test_il_y_a_des_documents_a_controler() -> None:
    """Sans ce contrôle, les suivants passeraient sur une liste vide.

    Un test paramétré sur une collection vide ne s'exécute jamais et compte
    pour un succès : la panne mesurerait alors sa propre absence.
    """
    assert DOCUMENTS, (
        f"Aucun Markdown trouvé sous {LABS} ni à la racine. Les contrôles de "
        "style porteraient sur une liste vide et passeraient sans rien mesurer."
    )


@pytest.mark.parametrize("document", DOCUMENTS, ids=identifiant)
def test_aucun_tiret_cadratin(document: Path) -> None:
    texte = document.read_text(encoding="utf-8")
    lignes = [
        f"  ligne {numero} : {ligne.strip()[:90]}"
        for numero, ligne in enumerate(texte.splitlines(), start=1)
        if CADRATIN in ligne
    ]
    assert not lignes, (
        f"{identifiant(document)} porte {len(lignes)} tiret(s) cadratin. "
        "Remplacez chacun par ce que la phrase demande, une virgule, un "
        "deux-points ou rien, et non par une substitution en masse qui "
        "abîmerait le texte.\n" + "\n".join(lignes[:10])
    )


@pytest.mark.parametrize("document", DOCUMENTS, ids=identifiant)
def test_aucun_emoji_decoratif(document: Path) -> None:
    texte = document.read_text(encoding="utf-8")
    lignes = [
        f"  ligne {numero} : {ligne.strip()[:90]}"
        for numero, ligne in enumerate(texte.splitlines(), start=1)
        if EMOJI.search(ligne)
    ]
    assert not lignes, (
        f"{identifiant(document)} porte {len(lignes)} ligne(s) avec un emoji "
        "décoratif. Ce catalogue n'en emploie pas : un repère de section se "
        "fait par un titre.\n" + "\n".join(lignes[:10])
    )
