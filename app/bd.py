"""Base de données SQLite.

Principe de minimisation (Loi 25) : on ne stocke NI les diapos NI les fiches.
Seulement : le compte (email + mot de passe chiffré), les crédits,
les achats (pour la comptabilité) et des statistiques de génération.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from . import config

_verrou = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS utilisateurs (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    mdp_hash TEXT NOT NULL,
    credits INTEGER NOT NULL DEFAULT 0,
    cree_le REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS achats (
    stripe_session TEXT PRIMARY KEY,
    utilisateur_id INTEGER,
    pack TEXT,
    credits INTEGER,
    montant INTEGER,
    devise TEXT,
    cree_le REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS generations (
    id TEXT PRIMARY KEY,
    utilisateur_id INTEGER,
    statut TEXT,
    pages INTEGER,
    tokens_entree INTEGER DEFAULT 0,
    tokens_sortie INTEGER DEFAULT 0,
    cree_le REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_gen_user ON generations(utilisateur_id, cree_le);
"""


def _connexion() -> sqlite3.Connection:
    Path(config.CHEMIN_BD).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(config.CHEMIN_BD, timeout=10)
    c.row_factory = sqlite3.Row
    return c


@contextmanager
def bd():
    with _verrou:
        c = _connexion()
        try:
            yield c
            c.commit()
        finally:
            c.close()


def initialiser() -> None:
    with bd() as c:
        c.executescript(SCHEMA)


# ---------- Utilisateurs ----------
def creer_utilisateur(email: str, mdp_hash: str) -> int | None:
    with bd() as c:
        try:
            cur = c.execute(
                "INSERT INTO utilisateurs(email, mdp_hash, credits, cree_le) VALUES (?,?,?,?)",
                (email, mdp_hash, config.CREDITS_GRATUITS, time.time()))
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None


def utilisateur_par_email(email: str):
    with bd() as c:
        return c.execute("SELECT * FROM utilisateurs WHERE email=?", (email,)).fetchone()


def utilisateur(uid: int):
    with bd() as c:
        return c.execute("SELECT * FROM utilisateurs WHERE id=?", (uid,)).fetchone()


def supprimer_utilisateur(uid: int) -> None:
    """Droit à l'effacement : on anonymise les achats (obligation comptable)."""
    with bd() as c:
        c.execute("DELETE FROM utilisateurs WHERE id=?", (uid,))
        c.execute("UPDATE achats SET utilisateur_id=NULL WHERE utilisateur_id=?", (uid,))
        c.execute("DELETE FROM generations WHERE utilisateur_id=?", (uid,))


# ---------- Crédits ----------
def reserver_credit(uid: int) -> bool:
    """Retire 1 crédit de façon atomique. False si solde insuffisant."""
    with bd() as c:
        cur = c.execute("UPDATE utilisateurs SET credits=credits-1 WHERE id=? AND credits>0", (uid,))
        return cur.rowcount == 1


def rendre_credit(uid: int) -> None:
    with bd() as c:
        c.execute("UPDATE utilisateurs SET credits=credits+1 WHERE id=?", (uid,))


def enregistrer_achat(session_id: str, uid: int, pack: str, credits: int, montant: int, devise: str) -> bool:
    """Idempotent : un même paiement Stripe ne crédite qu'une seule fois."""
    with bd() as c:
        try:
            c.execute("INSERT INTO achats VALUES (?,?,?,?,?,?,?)",
                      (session_id, uid, pack, credits, montant, devise, time.time()))
        except sqlite3.IntegrityError:
            return False
        c.execute("UPDATE utilisateurs SET credits=credits+? WHERE id=?", (credits, uid))
        return True


# ---------- Générations ----------
def debuter_generation(gid: str, uid: int, pages: int) -> None:
    with bd() as c:
        c.execute("INSERT INTO generations(id, utilisateur_id, statut, pages, cree_le) VALUES (?,?,?,?,?)",
                  (gid, uid, "en_cours", pages, time.time()))


def finir_generation(gid: str, statut: str, ti: int = 0, to: int = 0) -> None:
    with bd() as c:
        c.execute("UPDATE generations SET statut=?, tokens_entree=?, tokens_sortie=? WHERE id=?",
                  (statut, ti, to, gid))


def nb_generations_depuis(secondes: int, uid: int | None = None) -> int:
    limite = time.time() - secondes
    with bd() as c:
        if uid is None:
            return c.execute("SELECT COUNT(*) FROM generations WHERE cree_le>?", (limite,)).fetchone()[0]
        return c.execute("SELECT COUNT(*) FROM generations WHERE utilisateur_id=? AND cree_le>?",
                         (uid, limite)).fetchone()[0]


def generation_en_cours(uid: int) -> bool:
    with bd() as c:
        return c.execute(
            "SELECT 1 FROM generations WHERE utilisateur_id=? AND statut='en_cours' AND cree_le>?",
            (uid, time.time() - 900)).fetchone() is not None
