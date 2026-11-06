"""Assemblage et compilation sécurisée des fiches LaTeX.

Sécurité : le corps de la fiche vient d'une IA qui a lu des diapos
envoyées par n'importe qui. Un document piégé pourrait demander à l'IA
d'écrire ``\\input{/etc/passwd}`` pour voler des fichiers du serveur.
On bloque donc :
  1. les commandes dangereuses (liste noire ci-dessous) ;
  2. l'exécution de commandes shell (``-no-shell-escape``) ;
  3. la lecture/écriture hors du dossier de travail (``openin_any=p``) ;
  4. les compilations trop longues (délai maximum).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

PREAMBULE = (Path(__file__).parent / "latex" / "preambule.tex").read_text(encoding="utf-8")

# Commandes interdites dans le corps généré.
COMMANDES_INTERDITES = [
    "input", "include", "includeonly", "InputIfFileExists", "openin", "openout",
    "read", "readline", "write", "immediate", "newwrite", "newread", "write18",
    "ShellEscape", "directlua", "luaexec", "catcode", "csname", "endcsname",
    "def", "edef", "gdef", "xdef", "let", "futurelet", "expandafter",
    "documentclass", "usepackage", "RequirePackage", "includegraphics",
    "verbatiminput", "lstinputlisting", "openany", "special", "pdfobj",
    "pdfliteral", "pdffiledump", "pdfximage", "jobname", "loop", "repeat",
]
_RE_INTERDIT = re.compile(r"\\(" + "|".join(map(re.escape, COMMANDES_INTERDITES)) + r")(?![A-Za-z@])")
_RE_CORPS = re.compile(r"\\begin\{document\}(.*?)\\end\{document\}", re.S)
_RE_BLOC_CODE = re.compile(r"^```[a-zA-Z]*\s*\n|\n```\s*$")


class LatexInterdit(ValueError):
    """Le corps contient une commande refusée."""


@dataclass
class ResultatCompilation:
    ok: bool
    pdf: bytes | None
    log: str


def nettoyer_corps(texte: str) -> str:
    """Retire les ```latex, un éventuel préambule, et vérifie la sécurité."""
    texte = texte.strip()
    texte = _RE_BLOC_CODE.sub("", texte).strip()
    m = _RE_CORPS.search(texte)
    if m:
        texte = m.group(1).strip()
    texte = texte.replace("\\maketitle", "")
    m = _RE_INTERDIT.search(texte)
    if m:
        raise LatexInterdit(f"Commande LaTeX interdite : \\{m.group(1)}")
    if "^^" in texte:  # astuce TeX pour contourner la liste noire
        raise LatexInterdit("Séquence ^^ interdite")
    return texte


def echapper_texte(s: str) -> str:
    """Échappe un texte simple (ex. titre) pour LaTeX."""
    rep = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
           "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(rep.get(c, c) for c in s)


def assembler(corps: str, titre: str, sous_titre: str = "") -> str:
    t = echapper_texte(titre)
    st = echapper_texte(sous_titre)
    entete = (
        "\\begin{center}\n"
        f"{{\\LARGE\\bfseries\\color{{fBleu}} {t}}}\\\\[2pt]\n"
        + (f"{{\\small\\color{{fGris}} {st}}}\\\\[2pt]\n" if st else "")
        + "\\textcolor{fBleu}{\\rule{0.5\\linewidth}{1.2pt}}\n\\end{center}\n"
    )
    return (
        PREAMBULE
        + f"\n\\newcommand{{\\ficheTitre}}{{{t}}}\n"
        + "\\begin{document}\n" + entete + "\n" + corps + "\n\\end{document}\n"
    )


def _extraire_erreurs(log: str, max_lignes: int = 40) -> str:
    lignes = log.splitlines()
    out = []
    for i, l in enumerate(lignes):
        if l.startswith("!") or "Error" in l:
            out.extend(lignes[i:i + 4])
    return "\n".join(out[:max_lignes]) or "\n".join(lignes[-max_lignes:])


def compiler(source: str, delai: int = 60) -> ResultatCompilation:
    """Compile deux fois (pour les références) dans un dossier temporaire."""
    if not shutil.which("pdflatex"):
        return ResultatCompilation(False, None, "pdflatex introuvable sur le serveur")
    with tempfile.TemporaryDirectory(prefix="fiche_") as d:
        tex = Path(d) / "fiche.tex"
        tex.write_text(source, encoding="utf-8")
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": d,
            "openin_any": "p",   # lecture limitée au dossier courant
            "openout_any": "p",  # écriture limitée au dossier courant
            "shell_escape": "f",
            "TEXMFOUTPUT": d,
        }
        cmd = ["pdflatex", "-no-shell-escape", "-interaction=nonstopmode",
               "-halt-on-error", "fiche.tex"]
        log = ""
        try:
            for _ in range(2):
                p = subprocess.run(cmd, cwd=d, env=env, capture_output=True, timeout=delai)
                log = (Path(d) / "fiche.log").read_text(encoding="utf-8", errors="replace") \
                    if (Path(d) / "fiche.log").exists() else p.stdout.decode(errors="replace")
                if p.returncode != 0:
                    return ResultatCompilation(False, None, _extraire_erreurs(log))
        except subprocess.TimeoutExpired:
            return ResultatCompilation(False, None, "Compilation trop longue (délai dépassé)")
        pdf = Path(d) / "fiche.pdf"
        if not pdf.exists():
            return ResultatCompilation(False, None, _extraire_erreurs(log))
        return ResultatCompilation(True, pdf.read_bytes(), "")
