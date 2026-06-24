"""Stripe webhook validator."""

from __future__ import annotations

import hmac
import hashlib

from fastapi import Request, HTTPException


def verify_stripe_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not secret:
        return False
    try:
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, f"v1={expected}")
    except Exception:
        return False


async def parse_stripe_event(request: Request) -> dict:
    signature = request.headers.get("stripe-signature", "")
    payload = await request.body()
    secret = __import__("os").environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not verify_stripe_signature(payload, signature, secret):
        raise HTTPException(status_code=401, detail="Invalid stripe signature")
    try:
        return __import__("json").loads(payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
