import io
import time

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def _pdf_min():
    from pypdf import PdfWriter
    w = PdfWriter(); w.add_blank_page(200, 200)
    b = io.BytesIO(); w.write(b); return b.getvalue()


def _compte(email):
    r = c.post("/api/inscription", json={"email": email, "mdp": "motdepasse1", "accepte": True})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["jeton"]}


def test_inscription_connexion_et_profil():
    h = _compte("api1@test.ca")
    assert c.get("/api/moi", headers=h).json()["credits"] == 2
    r = c.post("/api/connexion", json={"email": "api1@test.ca", "mdp": "motdepasse1"})
    assert r.status_code == 200 and r.json()["profil"]["email"] == "api1@test.ca"
    assert c.post("/api/connexion", json={"email": "api1@test.ca", "mdp": "mauvais!!"}).status_code == 401
    assert c.post("/api/inscription", json={"email": "api1@test.ca", "mdp": "motdepasse1",
                                            "accepte": True}).status_code == 409


def test_jeton_obligatoire_et_falsifie():
    assert c.get("/api/moi").status_code == 401
    assert c.get("/api/moi", headers={"Authorization": "Bearer faux.jeton"}).status_code == 401


def test_generation_par_api():
    h = _compte("api2@test.ca")
    r = c.post("/api/generer", headers=h, data={"niveau": "synthetique"},
               files={"fichier": ("cours.pdf", _pdf_min(), "application/pdf")})
    assert r.status_code == 200, r.text
    gid = r.json()["id"]
    for _ in range(60):
        s = c.get(f"/api/fiche/{gid}", headers=h).json()
        if s["statut"] != "en_cours":
            break
        time.sleep(0.5)
    assert s["statut"] == "termine"
    assert c.get(f"/api/fiche/{gid}/pdf", headers=h).content.startswith(b"%PDF")
    assert c.get("/api/moi", headers=h).json()["credits"] == 1
    # un autre compte ne peut pas lire cette fiche
    assert c.get(f"/api/fiche/{gid}/pdf", headers=_compte("api3@test.ca")).status_code == 404


def test_sans_credit_402():
    h = _compte("api4@test.ca")
    from app import bd
    uid = bd.utilisateur_par_email("api4@test.ca")["id"]
    while bd.reserver_credit(uid):
        pass
    r = c.post("/api/generer", headers=h, files={"fichier": ("c.pdf", _pdf_min(), "application/pdf")})
    assert r.status_code == 402


def test_suppression_compte_invalide_le_jeton():
    h = _compte("api5@test.ca")
    assert c.delete("/api/compte", headers=h).status_code == 200
    assert c.get("/api/moi", headers=h).status_code == 401
