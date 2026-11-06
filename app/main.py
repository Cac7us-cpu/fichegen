"""Application web FicheGen (FastAPI).

Lancer en local :  uvicorn app.main:app --reload
"""
from __future__ import annotations

import re
import secrets
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import bcrypt
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from fichegen.extraction import FichierInvalide, lire_diapos
from fichegen.generateur import ClientAnthropic, EchecGeneration, NIVEAUX, Options, generer_fiche

from . import bd, config, paiement
from .demo import ClientDemo

ICI = Path(__file__).parent

if not config.SECRET_KEY:
    if config.PRODUCTION:
        raise RuntimeError("SECRET_KEY manquante : définis-la dans les variables d'environnement.")
    config.SECRET_KEY = secrets.token_hex(32)  # local uniquement

app = FastAPI(title=config.NOM_SERVICE, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(SessionMiddleware, secret_key=config.SECRET_KEY, same_site="lax",
                   https_only=config.PRODUCTION, max_age=60 * 60 * 24 * 14)
app.mount("/static", StaticFiles(directory=ICI / "static"), name="static")
gabarits = Jinja2Templates(directory=ICI / "templates")
gabarits.env.globals.update(service=config.NOM_SERVICE, packs=config.PACKS,
                            contact=config.CONTACT, credits_gratuits=config.CREDITS_GRATUITS)

bd.initialiser()

# Travaux en mémoire : les PDF ne touchent jamais le disque et expirent vite.
TRAVAUX: dict[str, dict] = {}
_verrou_travaux = threading.Lock()
_executeur = ThreadPoolExecutor(max_workers=3)
DUREE_VIE_FICHE = 30 * 60  # 30 minutes


@app.middleware("http")
async def entetes_securite(request: Request, call_next):
    rep = await call_next(request)
    rep.headers["X-Content-Type-Options"] = "nosniff"
    rep.headers["X-Frame-Options"] = "DENY"
    rep.headers["Referrer-Policy"] = "same-origin"
    if config.PRODUCTION:
        rep.headers["Strict-Transport-Security"] = "max-age=31536000"
    return rep


# ---------------------------------------------------------------- utilitaires
def _ia():
    if config.MODE_DEMO or not config.ANTHROPIC_API_KEY:
        return ClientDemo()
    return ClientAnthropic(api_key=config.ANTHROPIC_API_KEY, modele=config.CLAUDE_MODEL)


def _jeton_csrf(request: Request) -> str:
    if "csrf" not in request.session:
        request.session["csrf"] = secrets.token_urlsafe(24)
    return request.session["csrf"]


def _verifier_csrf(request: Request, jeton: str) -> None:
    if not jeton or not secrets.compare_digest(jeton, request.session.get("csrf", "")):
        raise HTTPException(400, "Formulaire expiré, recharge la page.")


def _moi(request: Request):
    uid = request.session.get("uid")
    return bd.utilisateur(uid) if uid else None


def _page(request: Request, nom: str, **ctx):
    ctx.update(request=request, moi=_moi(request), csrf=_jeton_csrf(request),
               message=request.session.pop("message", None))
    return gabarits.TemplateResponse(request, nom, ctx)


def _rediriger(url: str, message: str | None = None, request: Request | None = None):
    if message and request is not None:
        request.session["message"] = message
    return RedirectResponse(url, status_code=303)


def _nettoyer_travaux():
    maintenant = time.time()
    with _verrou_travaux:
        for gid in [g for g, t in TRAVAUX.items() if t["expire"] < maintenant]:
            del TRAVAUX[gid]


EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[a-zA-Z]{2,}$")


# ---------------------------------------------------------------- pages publiques
@app.get("/", response_class=HTMLResponse)
def accueil(request: Request):
    return _page(request, "accueil.html")


@app.get("/tarifs", response_class=HTMLResponse)
def tarifs(request: Request):
    return _page(request, "tarifs.html")


@app.get("/confidentialite", response_class=HTMLResponse)
def confidentialite(request: Request):
    return _page(request, "confidentialite.html", responsable=config.RESPONSABLE_RP)


@app.get("/conditions", response_class=HTMLResponse)
def conditions(request: Request):
    return _page(request, "conditions.html")


@app.get("/sante")
def sante():
    return {"ok": True}


# ---------------------------------------------------------------- comptes
@app.get("/inscription", response_class=HTMLResponse)
def inscription_form(request: Request):
    return _page(request, "inscription.html")


@app.post("/inscription")
def inscription(request: Request, email: str = Form(...), mdp: str = Form(...),
                accepte: str = Form(""), csrf: str = Form("")):
    _verifier_csrf(request, csrf)
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        return _rediriger("/inscription", "Adresse courriel invalide.", request)
    if len(mdp) < 8:
        return _rediriger("/inscription", "Le mot de passe doit faire au moins 8 caractères.", request)
    if accepte != "oui":
        return _rediriger("/inscription", "Tu dois accepter les conditions et la politique de confidentialité.", request)
    h = bcrypt.hashpw(mdp.encode()[:72], bcrypt.gensalt()).decode()
    uid = bd.creer_utilisateur(email, h)
    if uid is None:
        return _rediriger("/connexion", "Un compte existe déjà avec ce courriel. Connecte-toi.", request)
    request.session.clear()
    request.session["uid"] = uid
    return _rediriger("/tableau", f"Bienvenue ! Tu as {config.CREDITS_GRATUITS} fiches gratuites.", request)


@app.get("/connexion", response_class=HTMLResponse)
def connexion_form(request: Request):
    return _page(request, "connexion.html")


@app.post("/connexion")
def connexion(request: Request, email: str = Form(...), mdp: str = Form(...), csrf: str = Form("")):
    _verifier_csrf(request, csrf)
    u = bd.utilisateur_par_email(email.strip().lower())
    if not u or not bcrypt.checkpw(mdp.encode()[:72], u["mdp_hash"].encode()):
        time.sleep(0.5)
        return _rediriger("/connexion", "Courriel ou mot de passe incorrect.", request)
    request.session.clear()
    request.session["uid"] = u["id"]
    return _rediriger("/tableau")


@app.post("/deconnexion")
def deconnexion(request: Request, csrf: str = Form("")):
    _verifier_csrf(request, csrf)
    request.session.clear()
    return _rediriger("/")


@app.post("/compte/supprimer")
def supprimer_compte(request: Request, csrf: str = Form(""), confirmation: str = Form("")):
    _verifier_csrf(request, csrf)
    moi = _moi(request)
    if not moi:
        return _rediriger("/connexion")
    if confirmation.strip().upper() != "SUPPRIMER":
        return _rediriger("/tableau", "Écris SUPPRIMER pour confirmer.", request)
    bd.supprimer_utilisateur(moi["id"])
    request.session.clear()
    return _rediriger("/", "Ton compte et tes données ont été supprimés.", request)


# ---------------------------------------------------------------- génération
@app.get("/tableau", response_class=HTMLResponse)
def tableau(request: Request):
    moi = _moi(request)
    if not moi:
        return _rediriger("/connexion")
    return _page(request, "tableau.html", niveaux=NIVEAUX, taille_max=config.TAILLE_MAX_MO,
                 demo=config.MODE_DEMO or not config.ANTHROPIC_API_KEY,
                 paiement_actif=paiement.actif())


@app.post("/generer")
async def generer(request: Request, fichier: UploadFile = File(...), titre: str = Form(""),
                  niveau: str = Form("standard"), langue: str = Form("français"),
                  consignes: str = Form(""), csrf: str = Form("")):
    _verifier_csrf(request, csrf)
    moi = _moi(request)
    if not moi:
        return _rediriger("/connexion")
    uid = moi["id"]

    if bd.generation_en_cours(uid):
        return _rediriger("/tableau", "Une fiche est déjà en cours. Attends qu'elle se termine.", request)
    if bd.nb_generations_depuis(3600, uid) >= config.FICHES_PAR_HEURE:
        return _rediriger("/tableau", "Limite horaire atteinte, réessaie un peu plus tard.", request)
    if bd.nb_generations_depuis(86400) >= config.FICHES_PAR_JOUR_TOTAL:
        return _rediriger("/tableau", "Le service est très sollicité aujourd'hui. Réessaie demain.", request)

    data = await fichier.read(config.TAILLE_MAX_MO * 1024 * 1024 + 1)
    if len(data) > config.TAILLE_MAX_MO * 1024 * 1024:
        return _rediriger("/tableau", f"Fichier trop lourd (max {config.TAILLE_MAX_MO} Mo).", request)
    try:
        diapos = lire_diapos(fichier.filename or "", data)
    except FichierInvalide as e:
        return _rediriger("/tableau", str(e), request)
    del data

    if not bd.reserver_credit(uid):
        return _rediriger("/tarifs", "Tu n'as plus de crédits. Choisis un pack pour continuer.", request)

    titre = (titre.strip() or Path(fichier.filename or "Fiche").stem.replace("_", " "))[:120]
    opts = Options(titre=titre, niveau=niveau if niveau in NIVEAUX else "standard",
                   langue=langue if langue in ("français", "anglais") else "français",
                   consignes=consignes[:500])
    gid = uuid.uuid4().hex
    bd.debuter_generation(gid, uid, diapos.nb_pages)
    with _verrou_travaux:
        TRAVAUX[gid] = {"uid": uid, "statut": "en_cours", "etape": "En file d'attente…",
                        "pdf": None, "nom": re.sub(r"[^\w\-]+", "_", titre)[:60] or "fiche",
                        "erreur": None, "expire": time.time() + DUREE_VIE_FICHE}

    def tache():
        def etape(m):
            TRAVAUX[gid]["etape"] = m
        try:
            res = generer_fiche(diapos, opts, _ia(), progression=etape)
            TRAVAUX[gid].update(statut="termine", pdf=res.pdf, etape="Terminé")
            bd.finir_generation(gid, "termine", res.tokens_entree, res.tokens_sortie)
        except Exception as e:  # remboursement automatique
            bd.rendre_credit(uid)
            bd.finir_generation(gid, "echec")
            msg = str(e) if isinstance(e, EchecGeneration) else "Erreur interne pendant la génération."
            TRAVAUX[gid].update(statut="echec", erreur=msg + " Ton crédit a été remboursé.")

    _nettoyer_travaux()
    _executeur.submit(tache)
    return RedirectResponse(f"/fiche/{gid}", status_code=303)


def _travail(request: Request, gid: str) -> dict:
    t = TRAVAUX.get(gid)
    if not t or t["uid"] != request.session.get("uid"):
        raise HTTPException(404, "Fiche introuvable ou expirée.")
    return t


@app.get("/fiche/{gid}", response_class=HTMLResponse)
def page_fiche(request: Request, gid: str):
    t = _travail(request, gid)
    return _page(request, "fiche.html", gid=gid, t=t)


@app.get("/fiche/{gid}/statut")
def statut_fiche(request: Request, gid: str):
    t = _travail(request, gid)
    return JSONResponse({"statut": t["statut"], "etape": t["etape"], "erreur": t["erreur"]})


@app.get("/fiche/{gid}/pdf")
def telecharger(request: Request, gid: str):
    t = _travail(request, gid)
    if t["statut"] != "termine" or not t["pdf"]:
        raise HTTPException(404, "Fiche pas encore prête.")
    return Response(t["pdf"], media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{t["nom"]}_fiche.pdf"',
        "Cache-Control": "no-store"})


# ---------------------------------------------------------------- paiement
@app.post("/acheter/{pack}")
def acheter(request: Request, pack: str, csrf: str = Form("")):
    _verifier_csrf(request, csrf)
    moi = _moi(request)
    if not moi:
        return _rediriger("/inscription", "Crée un compte avant d'acheter des crédits.", request)
    if pack not in config.PACKS:
        raise HTTPException(404)
    if not paiement.actif():
        return _rediriger("/tarifs", "Le paiement n'est pas encore activé.", request)
    return RedirectResponse(paiement.creer_session(moi["id"], moi["email"], pack), status_code=303)


@app.get("/paiement/merci", response_class=HTMLResponse)
def merci(request: Request):
    return _rediriger("/tableau", "Merci ! Tes crédits apparaîtront dans quelques secondes.", request)


@app.post("/stripe/webhook")
async def webhook(request: Request):
    corps = await request.body()
    ok = paiement.traiter_webhook(corps, request.headers.get("stripe-signature", ""))
    if not ok:
        raise HTTPException(400, "Signature invalide")
    return {"recu": True}
