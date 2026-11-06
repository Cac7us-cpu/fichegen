"""Configuration lue dans les variables d'environnement (fichier .env).

Aucune clé secrète ne doit jamais être écrite dans le code ni envoyée sur GitHub.
"""
from __future__ import annotations

import os
from pathlib import Path


def _charger_env(fichier: Path = Path(".env")) -> None:
    """Mini-lecteur de .env (évite une dépendance)."""
    if not fichier.exists():
        return
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        k, v = ligne.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_charger_env()


def _int(nom: str, defaut: int) -> int:
    try:
        return int(os.environ.get(nom, defaut))
    except ValueError:
        return defaut


NOM_SERVICE = os.environ.get("NOM_SERVICE", "FicheGen")
URL_SITE = os.environ.get("URL_SITE", "http://localhost:8000").rstrip("/")
SECRET_KEY = os.environ.get("SECRET_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
CHEMIN_BD = os.environ.get("CHEMIN_BD", "donnees/fichegen.db")
CONTACT = os.environ.get("CONTACT_EMAIL", "contact@example.com")
RESPONSABLE_RP = os.environ.get("RESPONSABLE_RP", "Le fondateur de FicheGen")

CREDITS_GRATUITS = _int("CREDITS_GRATUITS", 2)
TAILLE_MAX_MO = _int("TAILLE_MAX_MO", 25)
FICHES_PAR_HEURE = _int("FICHES_PAR_HEURE", 6)          # par utilisateur
FICHES_PAR_JOUR_TOTAL = _int("FICHES_PAR_JOUR_TOTAL", 300)  # garde-fou global (budget)
MODE_DEMO = os.environ.get("MODE_DEMO", "0") == "1"     # IA simulée, pour tester sans clé

# Packs de crédits (prix en cents CAD). Modifie librement.
PACKS = {
    "decouverte": {"nom": "Découverte", "credits": 5, "prix": 299},
    "session": {"nom": "Session", "credits": 15, "prix": 699},
    "examens": {"nom": "Période d'examens", "credits": 40, "prix": 1499},
}
DEVISE = "cad"

PRODUCTION = URL_SITE.startswith("https://")

# Origines autorisées à appeler l'API depuis un navigateur (tests de l'app en version web).
# Les applications iPhone/Android n'en ont pas besoin. Ex. : http://localhost:8081
CORS_ORIGINES = [o.strip() for o in os.environ.get("CORS_ORIGINES", "").split(",") if o.strip()]
