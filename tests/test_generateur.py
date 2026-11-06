from fichegen.extraction import Diapos
from fichegen.generateur import EchecGeneration, Options, generer_fiche


class IAFaussee:
    def __init__(self, reponses):
        self.reponses = list(reponses)
        self.appels = 0

    def generer(self, systeme, contenu, max_tokens):
        self.appels += 1
        return self.reponses.pop(0), 100, 50


D = Diapos("texte", None, "--- Diapo 1 ---\nOffre et demande", 1)


def test_generation_ok():
    ia = IAFaussee([r"\section{Offre}Texte."])
    r = generer_fiche(D, Options(titre="Test"), ia)
    assert r.pdf.startswith(b"%PDF") and ia.appels == 1


def test_correction_automatique():
    ia = IAFaussee([r"\section{A} $x", r"\section{A} $x$"])
    r = generer_fiche(D, Options(), ia)
    assert r.tentatives == 2 and r.tokens_entree == 200


def test_commande_interdite_puis_correction():
    ia = IAFaussee([r"\input{/etc/passwd}", r"\section{Propre}"])
    assert generer_fiche(D, Options(), ia).tentatives == 2


def test_echec_definitif():
    ia = IAFaussee([r"$x"] * 3)
    try:
        generer_fiche(D, Options(), ia)
        assert False
    except EchecGeneration:
        pass
