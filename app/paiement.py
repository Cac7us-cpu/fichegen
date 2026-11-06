"""Paiements Stripe (Checkout + webhook).

Les numéros de carte ne passent JAMAIS par notre serveur : l'étudiant
paie sur la page sécurisée de Stripe, puis Stripe nous prévient via le
webhook. C'est le webhook (signé) qui ajoute les crédits, pas la page
« merci » — sinon n'importe qui pourrait s'ajouter des crédits.
"""
from __future__ import annotations

import json
import logging

from . import bd, config

log = logging.getLogger("fichegen.paiement")


def actif() -> bool:
    return bool(config.STRIPE_SECRET_KEY and config.STRIPE_WEBHOOK_SECRET)


def _stripe():
    import stripe
    stripe.api_key = config.STRIPE_SECRET_KEY
    return stripe


def creer_session(uid: int, email: str, pack_id: str) -> str:
    pack = config.PACKS[pack_id]
    s = _stripe().checkout.Session.create(
        mode="payment",
        customer_email=email,
        line_items=[{
            "quantity": 1,
            "price_data": {
                "currency": config.DEVISE,
                "unit_amount": pack["prix"],
                "product_data": {"name": f"{config.NOM_SERVICE} — {pack['nom']} ({pack['credits']} fiches)"},
            },
        }],
        metadata={"uid": str(uid), "pack": pack_id},
        success_url=f"{config.URL_SITE}/paiement/merci",
        cancel_url=f"{config.URL_SITE}/tarifs",
    )
    return s.url


def traiter_webhook(corps: bytes, signature: str) -> bool:
    stripe = _stripe()
    try:
        stripe.WebhookSignature.verify_header(corps.decode("utf-8"), signature,
                                              config.STRIPE_WEBHOOK_SECRET, 300)
        evt = json.loads(corps)
    except Exception:
        log.warning("Webhook Stripe refusé (signature invalide)")
        return False
    if evt["type"] in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        s = evt["data"]["object"]
        if s.get("payment_status") != "paid":
            return True
        md = s.get("metadata") or {}
        pack = config.PACKS.get(md.get("pack", ""))
        if not pack or not md.get("uid", "").isdigit():
            log.error("Webhook sans métadonnées valides : %s", s.get("id"))
            return True
        if s.get("amount_total") != pack["prix"]:
            log.error("Montant inattendu pour %s", s.get("id"))
            return True
        bd.enregistrer_achat(s["id"], int(md["uid"]), md["pack"], pack["credits"],
                             s.get("amount_total") or 0, s.get("currency") or config.DEVISE)
    return True
