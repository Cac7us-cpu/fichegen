import hashlib
import hmac
import io
import json
import re
import time

from fastapi.testclient import TestClient

from app import bd, config
from app.main import app


def _csrf(c, url):
    return re.search(r'name="csrf" value="([^"]+)"', c.get(url).text).group(1)


def _inscrire(c, email):
    return c.post("/inscription", data={"email": email, "mdp": "motdepasse1", "accepte": "oui",
                                        "csrf": _csrf(c, "/inscription")})


def _pdf_min():
    from pypdf import PdfWriter
    w = PdfWriter(); w.add_blank_page(200, 200)
    b = io.BytesIO(); w.write(b); return b.getvalue()


def test_pages_publiques():
    c = TestClient(app)
    for u in ["/", "/tarifs", "/confidentialite", "/conditions", "/inscription", "/connexion"]:
        assert c.get(u).status_code == 200


def test_parcours_complet_et_credits():
    c = TestClient(app)
    _inscrire(c, "a@test.ca")
    assert "2 crédits" in c.get("/tableau").text
    csrf = _csrf(c, "/tableau")
    r = c.post("/generer", data={"csrf": csrf, "niveau": "standard"},
               files={"fichier": ("cours.pdf", _pdf_min(), "application/pdf")}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/fiche/")
    url = r.headers["location"]
    for _ in range(60):
        s = c.get(url + "/statut").json()
        if s["statut"] != "en_cours":
            break
        time.sleep(0.5)
    assert s["statut"] == "termine", s
    pdf = c.get(url + "/pdf")
    assert pdf.content.startswith(b"%PDF")
    assert "1 crédit" in c.get("/tableau").text
    # un autre utilisateur ne peut pas voir la fiche
    c2 = TestClient(app)
    _inscrire(c2, "b@test.ca")
    assert c2.get(url + "/pdf").status_code == 404


def test_csrf_obligatoire():
    c = TestClient(app)
    r = c.post("/inscription", data={"email": "x@test.ca", "mdp": "motdepasse1", "accepte": "oui"})
    assert r.status_code == 400


def test_fichier_invalide_ne_consomme_pas_de_credit():
    c = TestClient(app)
    _inscrire(c, "c@test.ca")
    c.post("/generer", data={"csrf": _csrf(c, "/tableau")},
           files={"fichier": ("x.pdf", b"pas un pdf", "application/pdf")})
    assert "2 crédits" in c.get("/tableau").text


def _signer(corps: bytes, secret: str) -> str:
    t = str(int(time.time()))
    sig = hmac.new(secret.encode(), f"{t}.".encode() + corps, hashlib.sha256).hexdigest()
    return f"t={t},v1={sig}"


def test_webhook_stripe_credite_une_seule_fois():
    c = TestClient(app)
    _inscrire(c, "d@test.ca")
    uid = bd.utilisateur_par_email("d@test.ca")["id"]
    pack = config.PACKS["session"]
    evt = {"type": "checkout.session.completed", "data": {"object": {
        "id": "cs_test_1", "payment_status": "paid", "amount_total": pack["prix"], "currency": "cad",
        "metadata": {"uid": str(uid), "pack": "session"}}}}
    corps = json.dumps(evt).encode()
    for _ in range(2):  # Stripe peut renvoyer le même événement
        r = c.post("/stripe/webhook", content=corps,
                   headers={"stripe-signature": _signer(corps, config.STRIPE_WEBHOOK_SECRET)})
        assert r.status_code == 200
    assert bd.utilisateur(uid)["credits"] == 2 + pack["credits"]


def test_webhook_signature_invalide_refusee():
    c = TestClient(app)
    r = c.post("/stripe/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=faux"})
    assert r.status_code == 400


def test_suppression_compte():
    c = TestClient(app)
    _inscrire(c, "e@test.ca")
    c.post("/compte/supprimer", data={"csrf": _csrf(c, "/tableau"), "confirmation": "SUPPRIMER"})
    assert bd.utilisateur_par_email("e@test.ca") is None
