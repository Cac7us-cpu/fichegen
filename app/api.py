"""API JSON utilisée par l'application mobile (iPhone / Android).

Authentification : l'app reçoit un jeton signé à la connexion et l'envoie
ensuite dans l'en-tête ``Authorization: Bearer <jeton>``. Le jeton est
signé avec SECRET_KEY : impossible à fabriquer sans la clé du serveur.
"""
from __future__ import annotations

import time

import bcrypt
from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel

from fichegen.generateur import NIVEAUX

from . import bd, config, paiement

routeur = APIRouter(prefix="/api", tags=["mobile"])
DUREE_JETON = 60 * 60 * 24 * 30  # 30 jours


def _signeur() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(config.SECRET_KEY, salt="fichegen-api")


def creer_jeton(uid: int) -> str:
    return _signeur().dumps({"uid": uid})


def _utilisateur(authorization: str | None):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Connexion requise.")
    try:
        data = _signeur().loads(authorization[7:].strip(), max_age=DUREE_JETON)
    except SignatureExpired:
        raise HTTPException(401, "Session expirée, reconnecte-toi.")
    except BadSignature:
        raise HTTPException(401, "Jeton invalide.")
    u = bd.utilisateur(int(data.get("uid", 0)))
    if not u:
        raise HTTPException(401, "Compte introuvable.")
    return u


def _profil(u) -> dict:
    return {
        "email": u["email"],
        "credits": u["credits"],
        "paiement_actif": paiement.actif(),
        "packs": [{"id": k, **v} for k, v in config.PACKS.items()],
        "niveaux": list(NIVEAUX),
        "taille_max_mo": config.TAILLE_MAX_MO,
    }


class Identifiants(BaseModel):
    email: str
    mdp: str
    accepte: bool = False


@routeur.post("/inscription")
def inscription(ids: Identifiants):
    from .main import EMAIL_RE
    email = ids.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Adresse courriel invalide.")
    if len(ids.mdp) < 8:
        raise HTTPException(400, "Le mot de passe doit faire au moins 8 caractères.")
    if not ids.accepte:
        raise HTTPException(400, "Tu dois accepter les conditions et la politique de confidentialité.")
    h = bcrypt.hashpw(ids.mdp.encode()[:72], bcrypt.gensalt()).decode()
    uid = bd.creer_utilisateur(email, h)
    if uid is None:
        raise HTTPException(409, "Un compte existe déjà avec ce courriel.")
    return {"jeton": creer_jeton(uid), "profil": _profil(bd.utilisateur(uid))}


@routeur.post("/connexion")
def connexion(ids: Identifiants):
    u = bd.utilisateur_par_email(ids.email.strip().lower())
    if not u or not bcrypt.checkpw(ids.mdp.encode()[:72], u["mdp_hash"].encode()):
        time.sleep(0.5)
        raise HTTPException(401, "Courriel ou mot de passe incorrect.")
    return {"jeton": creer_jeton(u["id"]), "profil": _profil(u)}


@routeur.get("/moi")
def moi(authorization: str | None = Header(None)):
    return _profil(_utilisateur(authorization))


@routeur.post("/generer")
async def generer(fichier: UploadFile = File(...), titre: str = Form(""),
                  niveau: str = Form("standard"), langue: str = Form("français"),
                  consignes: str = Form(""), nom: str = Form(""),
                  authorization: str | None = Header(None)):
    from .main import lancer_generation
    u = _utilisateur(authorization)
    data = await fichier.read(config.TAILLE_MAX_MO * 1024 * 1024 + 1)
    nom_fichier = (nom or fichier.filename or "")[:200]  # l'app envoie le vrai nom du fichier
    gid, erreur, retour = lancer_generation(u["id"], nom_fichier, data,
                                            titre, niveau, langue, consignes)
    if erreur:
        raise HTTPException(402 if retour == "/tarifs" else 400, erreur)
    return {"id": gid}


def _travail(gid: str, authorization: str | None) -> dict:
    from .main import TRAVAUX
    u = _utilisateur(authorization)
    t = TRAVAUX.get(gid)
    if not t or t["uid"] != u["id"]:
        raise HTTPException(404, "Fiche introuvable ou expirée.")
    return t


@routeur.get("/fiche/{gid}")
def statut(gid: str, authorization: str | None = Header(None)):
    t = _travail(gid, authorization)
    return {"statut": t["statut"], "etape": t["etape"], "erreur": t["erreur"], "nom": t["nom"]}


@routeur.get("/fiche/{gid}/pdf")
def pdf(gid: str, authorization: str | None = Header(None)):
    t = _travail(gid, authorization)
    if t["statut"] != "termine" or not t["pdf"]:
        raise HTTPException(404, "Fiche pas encore prête.")
    return Response(t["pdf"], media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{t["nom"]}_fiche.pdf"',
        "Cache-Control": "no-store"})


@routeur.post("/acheter/{pack}")
def acheter(pack: str, authorization: str | None = Header(None)):
    u = _utilisateur(authorization)
    if pack not in config.PACKS:
        raise HTTPException(404, "Pack inconnu.")
    if not paiement.actif():
        raise HTTPException(503, "Le paiement n'est pas encore activé.")
    return {"url": paiement.creer_session(u["id"], u["email"], pack)}


@routeur.delete("/compte")
def supprimer(authorization: str | None = Header(None)):
    u = _utilisateur(authorization)
    bd.supprimer_utilisateur(u["id"])
    return {"supprime": True}
