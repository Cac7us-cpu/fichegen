import pytest

from fichegen.latex import LatexInterdit, assembler, compiler, nettoyer_corps


def test_compile_corps_simple():
    r = compiler(assembler(nettoyer_corps(r"\section{A}\begin{formule}$x^2$\end{formule}"), "Titre & co"))
    assert r.ok and r.pdf.startswith(b"%PDF")


@pytest.mark.parametrize("piege", [r"\input{/etc/passwd}", r"\include{x}", r"\write18{ls}",
                                   r"\immediate\write", r"\def\x{y}", r"\catcode`\^=7", r"^^5cinput"])
def test_commandes_dangereuses_bloquees(piege):
    with pytest.raises(LatexInterdit):
        nettoyer_corps("texte " + piege)


def test_nettoyage_bloc_code_et_preambule():
    brut = "```latex\n\\documentclass{article}\\begin{document}\\section{Ok}\\end{document}\n```"
    assert nettoyer_corps(brut) == r"\section{Ok}"


def test_lecture_fichier_systeme_impossible():
    r = compiler(assembler(r"\IfFileExists{/etc/passwd}{FUITE}{BLOQUE}", "x"))
    assert r.ok
    assert b"FUITE" not in r.pdf  # texte compressé, mais vérifions via pypdf
    from io import BytesIO
    from pypdf import PdfReader
    txt = "".join(p.extract_text() for p in PdfReader(BytesIO(r.pdf)).pages)
    assert "BLOQUE" in txt and "FUITE" not in txt


def test_erreur_de_compilation_renvoie_log():
    r = compiler(assembler(r"\begin{formule} $x \end{formule}", "x"))
    assert not r.ok and r.log
