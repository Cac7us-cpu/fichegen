"""Lecture des diapos envoyées (PDF ou PowerPoint)."""
from __future__ import annotations

import io
from dataclasses import dataclass

MAX_PAGES_PDF = 100          # limite de l'API pour un PDF envoyé tel quel
MAX_CARACTERES = 180_000     # garde-fou pour le coût d'un appel


class FichierInvalide(ValueError):
    pass


@dataclass
class Diapos:
    type: str                 # "pdf" ou "texte"
    pdf: bytes | None         # PDF brut (Claude lit aussi les images/formules)
    texte: str                # texte extrait (sert de secours et pour PPTX)
    nb_pages: int


def _texte_pdf(data: bytes) -> tuple[str, int]:
    from pypdf import PdfReader
    try:
        r = PdfReader(io.BytesIO(data))
        if r.is_encrypted:
            raise FichierInvalide("Le PDF est protégé par un mot de passe.")
        pages = [(p.extract_text() or "") for p in r.pages]
    except FichierInvalide:
        raise
    except Exception as e:  # PDF corrompu
        raise FichierInvalide("PDF illisible ou corrompu.") from e
    texte = "\n\n".join(f"--- Diapo {i + 1} ---\n{t.strip()}" for i, t in enumerate(pages))
    return texte, len(pages)


def _texte_pptx(data: bytes) -> tuple[str, int]:
    from pptx import Presentation
    try:
        prs = Presentation(io.BytesIO(data))
    except Exception as e:
        raise FichierInvalide("Fichier PowerPoint illisible.") from e
    blocs = []
    for i, slide in enumerate(prs.slides, 1):
        morceaux = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    t = "".join(run.text for run in para.runs).strip()
                    if t:
                        morceaux.append(("  " * para.level) + "- " + t)
            if getattr(shape, "has_table", False) and shape.has_table:
                for row in shape.table.rows:
                    morceaux.append(" | ".join(c.text.strip() for c in row.cells))
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                morceaux.append(f"[Notes du présentateur] {notes}")
        blocs.append(f"--- Diapo {i} ---\n" + "\n".join(morceaux))
    return "\n\n".join(blocs), len(prs.slides)


def lire_diapos(nom: str, data: bytes) -> Diapos:
    nom = nom.lower()
    if data[:4] == b"%PDF" or nom.endswith(".pdf"):
        if data[:4] != b"%PDF":
            raise FichierInvalide("Ce fichier n'est pas un vrai PDF.")
        texte, n = _texte_pdf(data)
        if n == 0:
            raise FichierInvalide("Le PDF ne contient aucune page.")
        if n > MAX_PAGES_PDF:
            raise FichierInvalide(f"Trop de pages ({n}). Maximum : {MAX_PAGES_PDF}.")
        return Diapos("pdf", data, texte[:MAX_CARACTERES], n)
    if nom.endswith(".pptx") and data[:2] == b"PK":
        texte, n = _texte_pptx(data)
        if not texte.strip():
            raise FichierInvalide("Aucun texte trouvé dans le PowerPoint.")
        return Diapos("texte", None, texte[:MAX_CARACTERES], n)
    raise FichierInvalide("Formats acceptés : PDF ou PowerPoint (.pptx).")
