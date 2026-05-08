"""
Razorpay payment gateway client for Indian customers.

Supports UPI, cards, NetBanking, and wallets through Razorpay Checkout.js.

API reference: https://razorpay.com/docs/api/
Authentication: key_id + key_secret (Basic Auth)
Signature verification: HMAC-SHA256

Public API:
  get_razorpay_client()                  → razorpay.Client (sync)
  create_order(amount_paise, ...)        → dict  — one-time payment order
  create_subscription(plan_id, ...)      → dict  — recurring subscription
  verify_payment_signature(...)          → bool  — post-payment verification
  verify_webhook_signature(body, sig)    → bool  — webhook authenticity check

All network calls are wrapped in asyncio.to_thread since razorpay SDK is sync.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
from typing import Any

from loguru import logger

from app.config import settings


def get_razorpay_client():
    """
    Return an authenticated Razorpay client instance.

    Uses RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET from settings.
    Raises ValueError if keys are not configured.
    """
    import razorpay

    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise ValueError(
            "RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are not configured. "
            "Get your keys from https://dashboard.razorpay.com/app/keys and set them in backend/.env"
        )
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


# ── Signature verification ─────────────────────────────────────────────────────

def verify_payment_signature(
    order_id: str,
    payment_id: str,
    signature: str,
) -> bool:
    """
    Verify a Razorpay payment signature after checkout completion.

    Algorithm (per Razorpay docs):
      source = "{order_id}|{payment_id}"
      expected = HMAC-SHA256(source, RAZORPAY_KEY_SECRET).hexdigest()
      return compare_digest(expected, signature)

    Args:
        order_id:   Razorpay order ID (razorpay_order_id from checkout handler).
        payment_id: Razorpay payment ID (razorpay_payment_id from checkout handler).
        signature:  razorpay_signature from the checkout handler response.

    Returns:
        True if signature is valid, False otherwise.
    """
    if not settings.RAZORPAY_KEY_SECRET:
        logger.warning("[razorpay] RAZORPAY_KEY_SECRET not configured — skipping verification")
        return True  # Fail-open in dev

    source = f"{order_id}|{payment_id}"
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        source.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    match = hmac.compare_digest(expected, signature.lower())
    if not match:
        logger.warning(
            f"[razorpay] Payment signature mismatch for order={order_id} "
            f"payment={payment_id}"
        )
    return match


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """
    Verify a Razorpay webhook signature.

    Razorpay sends X-Razorpay-Signature in the request header.
    Computed as HMAC-SHA256 of the raw request body using RAZORPAY_WEBHOOK_SECRET.

    Args:
        body:      Raw bytes of the webhook request body.
        signature: Value of the X-Razorpay-Signature header.

    Returns:
        True if signature is valid, False otherwise.
    """
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.warning("[razorpay] RAZORPAY_WEBHOOK_SECRET not configured — skipping verification")
        return True  # Fail-open in dev

    expected = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    match = hmac.compare_digest(expected, signature.lower())
    if not match:
        logger.warning("[razorpay] Webhook signature mismatch")
    return match


# ── Order creation (one-time payment) ─────────────────────────────────────────

async def create_order(
    amount_paise: int,
    currency: str = "INR",
    user_id: str = "",
    plan: str = "",
) -> dict[str, Any]:
    """
    Create a Razorpay order for one-time payment.

    Args:
        amount_paise: Amount in paise (₹1 = 100 paise). e.g. ₹2,499 = 249900.
        currency:     ISO currency code (default "INR").
        user_id:      Zentro Leads user ID — stored in order notes for webhook.
        plan:         Plan name — stored in order notes for webhook activation.

    Returns:
        Dict with keys: order_id, amount, currency

    Raises:
        ValueError if Razorpay keys not configured.
        Exception on Razorpay API errors.
    """
    client = get_razorpay_client()

    order_data = {
        "amount":          amount_paise,
        "currency":        currency,
        "receipt":         f"zentro_{user_id[:8]}_{plan}",
        "payment_capture": 1,  # Auto-capture on payment
        "notes": {
            "user_id": user_id,
            "plan":    plan,
        },
    }

    logger.info(
        f"[razorpay] Creating order for user={user_id} plan={plan} "
        f"amount=₹{amount_paise / 100:.0f}"
    )

    order = await asyncio.to_thread(client.order.create, order_data)

    logger.info(f"[razorpay] Order created: id={order.get('id')}")
    return {
        "order_id": order.get("id"),
        "amount":   order.get("amount"),
        "currency": order.get("currency"),
    }


# ── Subscription creation (recurring billing) ─────────────────────────────────

async def create_subscription(
    plan_id: str,
    user_id: str,
    email: str,
    contact: str,
    total_count: int = 12,
) -> dict[str, Any]:
    """
    Create a Razorpay subscription for recurring monthly billing.

    Requires a Razorpay Plan to be pre-configured in the Razorpay dashboard.
    Use ``create_order`` for one-time payments instead.

    Args:
        plan_id:     Razorpay Plan ID (create in dashboard → Products → Plans).
        user_id:     Zentro Leads user ID (stored in notes).
        email:       Customer email for subscription notifications.
        contact:     Customer phone number (international format, e.g. +919XXXXXXXXX).
        total_count: Billing cycles (12 = annual, 0 = unlimited).

    Returns:
        Dict with keys: subscription_id, short_url

    Raises:
        ValueError if Razorpay keys not configured.
        Exception on Razorpay API errors.
    """
    client = get_razorpay_client()

    subscription_data = {
        "plan_id":         plan_id,
        "total_count":     total_count,
        "notify_by_email": 1,
        "notify_by_sms":   1,
        "notes": {
            "user_id": user_id,
        },
        "addons": [],
    }

    if email or contact:
        subscription_data["customer_notify"] = 1

    logger.info(
        f"[razorpay] Creating subscription for user={user_id} plan_id={plan_id}"
    )

    sub = await asyncio.to_thread(client.subscription.create, subscription_data)

    logger.info(
        f"[razorpay] Subscription created: id={sub.get('id')} "
        f"url={sub.get('short_url')}"
    )
    return {
        "subscription_id": sub.get("id"),
        "short_url":       sub.get("short_url"),
    }
