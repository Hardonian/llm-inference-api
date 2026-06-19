"""Stripe webhook handler for dashboard monetization.

Usage:
- POST /api/billing/stripe-webhook
- Headers: Stripe-Signature, Secret from STRIPE_WEBHOOK_SECRET env var
- Events: checkout.session.completed, invoice.payment_succeeded, customer.subscription.deleted
"""

import os
import json
import hmac
import hashlib
import logging
from pathlib import Path
from fastapi import Request, HTTPException
from starlette.responses import JSONResponse

logger = logging.getLogger("stripe_webhook")

STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
BILLING_DB = Path(os.environ.get("BILLING_DB", "/home/scott/ai-lab/dashboard/billing.json"))


def _verify_signature(payload: bytes, signature: str) -> bool:
    """Verify Stripe webhook signature."""
    if not STRIPE_WEBHOOK_SECRET:
        return True  # Allow in demo mode
    try:
        expected = hmac.new(
            STRIPE_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, f"v1={expected}")
    except Exception:
        return False


def _record_billing(event: dict) -> None:
    """Record billing event to DB."""
    events = []
    if BILLING_DB.exists():
        events = json.loads(BILLING_DB.read_text())
    events.append({"event": event["type"], "data": event["data"], "ts": event.get("created", 0)})
    BILLING_DB.parent.mkdir(parents=True, exist_ok=True)
    BILLING_DB.write_text(json.dumps(events[-100:]))  # Keep last 100 events


async def stripe_webhook(request: Request) -> JSONResponse:
    """Handle incoming Stripe webhooks."""
    signature = request.headers.get("stripe-signature", "")
    payload = await request.body()

    if not _verify_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = json.loads(payload)
    event_type = event.get("type", "")

    logger.info(f"Stripe webhook: {event_type}")

    if event_type == "checkout.session.completed":
        # Grant lifetime access
        pass
    elif event_type == "invoice.payment_succeeded":
        # Extend managed subscription
        pass
    elif event_type == "customer.subscription.deleted":
        # Revoke managed access
        pass

    _record_billing(event)
    return JSONResponse({"status": "ok", "event": event_type})