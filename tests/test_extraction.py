import io

import pytest

from fichegen.extraction import FichierInvalide, lire_diapos


def test_pptx():
    from pptx import Presentation
    p = Presentation()
    s = p.slides.add_slide(p.slide_layouts[1])
    s.shapes.title.text = "Coût marginal"
    s.placeholders[1].text = "Cm = dCT/dQ"
    b = io.BytesIO(); p.save(b)
    d = lire_diapos("cours.pptx", b.getvalue())
    assert d.type == "texte" and "Coût marginal" in d.texte and d.nb_pages == 1


def test_format_refuse():
    with pytest.raises(FichierInvalide):
        lire_diapos("notes.docx", b"PK\x03\x04...")
