"""
Billplz FPX payment gateway client for Malaysian customers.

API reference: https://www.billplz.com/api
Authentication: HTTP Basic Auth (API key as username, empty password)
X-Signature: HMAC-SHA256 for webhook + redirect verification

Public API:
  create_bill(...)    → dict  — create a new bill, returns {bill_id, url, state}
  get_bill(bill_id)   → dict  — fetch bill status by ID
  verify_x_signature(data, sig) → bool — verify callback/redirect integrity
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

import httpx
from loguru import logger

from app.config import settings


def _base_url() -> str:
    """Return sandbox or production API base URL."""
    if settings.BILLPLZ_SANDBOX:
        return "https://www.billplz-sandbox.com/api/v3"
    return "https://www.billplz.com/api/v3"


def _auth() -> tuple[str, str]:
    """Return Basic Auth tuple (api_key, empty_password)."""
    return (settings.BILLPLZ_API_KEY, "")


# ── X-Signature verification ───────────────────────────────────────────────────

def verify_x_signature(data: dict[str, Any], x_signature: str) -> bool:
    """
    Verify a Billplz X-Signature.

    Algorithm (per Billplz docs):
      1. Take all key-value pairs, exclude the ``x_signature`` key itself.
      2. Sort pairs by key ascending (case-insensitive).
      3. Concatenate as ``key1|value1|key2|value2...`` (pipe-separated).
      4. Compute HMAC-SHA256 of that string using ``settings.BILLPLZ_X_SIGNATURE``.
      5. Compare hex digest with the received ``x_signature`` value.

    Returns:
        True if signatures match, False otherwise (or if X_SIGNATURE unconfigured).
    """
    if not settings.BILLPLZ_X_SIGNATURE:
        logger.warning("[billplz] BILLPLZ_X_SIGNATURE not configured — skipping verification")
        return True  # Fail-open in dev; tighten in production

    filtered = {k: str(v) for k, v in data.items() if k.lower() != "x_signature"}
    sorted_pairs = sorted(filtered.items(), key=lambda kv: kv[0].lower())
    source = "|".join(f"{k}|{v}" for k, v in sorted_pairs)

    expected = hmac.new(
        settings.BILLPLZ_X_SIGNATURE.encode("utf-8"),
        source.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    match = hmac.compare_digest(expected, x_signature.lower())
    if not match:
        logger.warning(
            f"[billplz] X-Signature mismatch — "
            f"expected={expected[:12]}… got={x_signature[:12]}…"
        )
    return match


# ── Bill creation ──────────────────────────────────────────────────────────────

async def create_bill(
    name: str,
    email: str,
    phone: str,
    amount_cents: int,
    description: str,
    user_id: str,
    plan: str,
    redirect_url: str,
    callback_url: str,
) -> dict[str, Any]:
    """
    Create a Billplz bill and return the payment URL.

    Args:
        name:          Payer's full name.
        email:         Payer's email address.
        phone:         Malaysian mobile number in 601XXXXXXXX format.
        amount_cents:  Amount in sen (RM × 100). e.g. RM 149.00 = 14900.
        description:   Bill description shown on the Billplz page.
        user_id:       Zentro Leads user ID (stored in reference_1).
        plan:          Plan name string (stored in reference_2).
        redirect_url:  URL Billplz redirects browser to after payment.
        callback_url:  Backend URL Billplz POSTs server-to-server update to.

    Returns:
        Dict with keys: bill_id, url, state, paid, amount
    
    Raises:
        httpx.HTTPStatusError on Billplz API errors.
        ValueError if BILLPLZ_API_KEY or BILLPLZ_COLLECTION_ID are not configured.
    """
    if not settings.BILLPLZ_API_KEY:
        raise ValueError(
            "BILLPLZ_API_KEY is not configured. "
            "Set it in backend/.env to enable FPX payments."
        )
    if not settings.BILLPLZ_COLLECTION_ID:
        raise ValueError(
            "BILLPLZ_COLLECTION_ID is not configured. "
            "Create a collection in your Billplz dashboard and set the ID in backend/.env."
        )

    # Normalise Malaysian phone: strip spaces/dashes, ensure starts with 60
    mobile = phone.strip().replace(" ", "").replace("-", "")
    if mobile.startswith("+"):
        mobile = mobile[1:]
    if mobile.startswith("0"):
        mobile = "6" + mobile  # 0123456789 → 60123456789

    payload = {
        "collection_id":    settings.BILLPLZ_COLLECTION_ID,
        "email":            email,
        "mobile":           mobile,
        "name":             name,
        "amount":           str(amount_cents),
        "description":      description[:200],      # Billplz 200-char limit
        "redirect_url":     redirect_url,
        "callback_url":     callback_url,
        "reference_1_label": "user_id",
        "reference_1":      user_id,
        "reference_2_label": "plan",
        "reference_2":      plan,
    }

    url = f"{_base_url()}/bills"
    logger.info(
        f"[billplz] Creating bill for user={user_id} plan={plan} "
        f"amount={amount_cents}sen sandbox={settings.BILLPLZ_SANDBOX}"
    )

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, data=payload, auth=_auth())

    if resp.status_code not in (200, 201):
        logger.error(
            f"[billplz] Bill creation failed: {resp.status_code} {resp.text[:500]}"
        )
        resp.raise_for_status()

    data = resp.json()
    logger.info(
        f"[billplz] Bill created: id={data.get('id')} url={data.get('url')}"
    )
    return {
        "bill_id": data.get("id"),
        "url":     data.get("url"),
        "state":   data.get("state"),
        "paid":    bool(data.get("paid", False)),
        "amount":  data.get("amount"),
    }


# ── Bill status fetch ──────────────────────────────────────────────────────────

async def get_bill(bill_id: str) -> dict[str, Any]:
    """
    Fetch a bill's current status from Billplz.

    Args:
        bill_id: Billplz bill ID (e.g. "8X0Iyzaw").

    Returns:
        Full bill dict from Billplz API.
    """
    url = f"{_base_url()}/bills/{bill_id}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, auth=_auth())
    resp.raise_for_status()
    return resp.json()
