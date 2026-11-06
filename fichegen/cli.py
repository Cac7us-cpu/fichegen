"""Commande terminal : ``fiche diapos.pdf [-o fiche.pdf] [--niveau standard]``."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .extraction import FichierInvalide, lire_diapos
from .generateur import ClientAnthropic, EchecGeneration, NIVEAUX, Options, generer_fiche


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="fiche", description="Transforme des diapos en fiche de révision LaTeX.")
    p.add_argument("diapos", type=Path, help="Fichier PDF ou PPTX")
    p.add_argument("-o", "--sortie", type=Path, help="PDF de sortie (défaut : <diapos>_fiche.pdf)")
    p.add_argument("-t", "--titre", help="Titre de la fiche")
    p.add_argument("-n", "--niveau", choices=list(NIVEAUX), default="standard")
    p.add_argument("-l", "--langue", default="français")
    p.add_argument("--tex", action="store_true", help="Garder aussi le fichier .tex")
    a = p.parse_args(argv)

    try:
        diapos = lire_diapos(a.diapos.name, a.diapos.read_bytes())
        opts = Options(titre=a.titre or a.diapos.stem.replace("_", " "), niveau=a.niveau, langue=a.langue)
        res = generer_fiche(diapos, opts, ClientAnthropic(), progression=lambda m: print("•", m))
    except (FichierInvalide, EchecGeneration, FileNotFoundError) as e:
        print("Erreur :", e, file=sys.stderr)
        return 1
    sortie = a.sortie or a.diapos.with_name(a.diapos.stem + "_fiche.pdf")
    sortie.write_bytes(res.pdf)
    if a.tex:
        sortie.with_suffix(".tex").write_text(res.tex, encoding="utf-8")
    print(f"✓ Fiche créée : {sortie}  ({res.tokens_entree} tokens lus, {res.tokens_sortie} écrits)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
