"""
Payment signature tests — pure unit tests.

No HTTP, no DB, no mocks. We call the signature functions directly with
pre-computed HMAC-SHA256 test vectors. The vectors are computed in this file
so they can be verified independently with any HMAC tool.
"""

from __future__ import annotations

import hashlib
import hmac

import pytest

from app.billing.billplz_client import verify_x_signature
from app.billing.razorpay_client import verify_payment_signature, verify_webhook_signature

# ── Test secrets (mirrors .env values set by conftest) ────────────────────────
BILLPLZ_SECRET = "test_x_sig_secret"
RAZORPAY_KEY_SECRET = "test_razorpay_secret"
RAZORPAY_WEBHOOK_SECRET = "test_webhook_secret"

# ── Billplz payload ────────────────────────────────────────────────────────────
BILLPLZ_PAYLOAD = {
    "id": "bill_test_123",
    "collection_id": "col_abc",
    "paid": "true",
    "state": "paid",
    "amount": "14900",
    "paid_amount": "14900",
    "due_at": "2026-06-01",
    "email": "agent@test.com",
    "mobile": "60123456789",
    "name": "Test Agent",
    "url": "https://www.billplz.com/bills/bill_test_123",
    "reference_1": "user_abc",
    "reference_2": "starter",
}


def _compute_billplz_sig(data: dict, secret: str) -> str:
    """Replicate Billplz X-Signature algorithm."""
    filtered = {k: str(v) for k, v in data.items() if k.lower() != "x_signature"}
    sorted_pairs = sorted(filtered.items(), key=lambda kv: kv[0].lower())
    source = "|".join(f"{k}|{v}" for k, v in sorted_pairs)
    return hmac.new(secret.encode(), source.encode(), hashlib.sha256).hexdigest()


def _compute_razorpay_pay_sig(order_id: str, payment_id: str, secret: str) -> str:
    source = f"{order_id}|{payment_id}"
    return hmac.new(secret.encode(), source.encode(), hashlib.sha256).hexdigest()


def _compute_razorpay_wh_sig(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ── Billplz X-Signature ────────────────────────────────────────────────────────

async def test_billplz_valid_signature():
    """A correctly computed signature verifies as True."""
    sig = _compute_billplz_sig(BILLPLZ_PAYLOAD, BILLPLZ_SECRET)
    assert verify_x_signature(BILLPLZ_PAYLOAD, sig) is True


async def test_billplz_invalid_signature():
    """A wrong signature is rejected."""
    assert verify_x_signature(BILLPLZ_PAYLOAD, "deadbeefdeadbeef" * 4) is False


async def test_billplz_tampered_payload():
    """
    Computing the signature against the original payload then changing a field
    must be detected — the tampering invalidates the signature.
    """
    sig = _compute_billplz_sig(BILLPLZ_PAYLOAD, BILLPLZ_SECRET)
    tampered = {**BILLPLZ_PAYLOAD, "paid": "false"}  # money flip
    assert verify_x_signature(tampered, sig) is False


async def test_billplz_signature_case_insensitive():
    """
    Signature comparison must be case-insensitive (HMAC hex may be upper or lower).
    """
    sig = _compute_billplz_sig(BILLPLZ_PAYLOAD, BILLPLZ_SECRET).upper()
    assert verify_x_signature(BILLPLZ_PAYLOAD, sig) is True


# ── Razorpay Payment Signature ─────────────────────────────────────────────────

ORDER_ID = "order_test_123"
PAYMENT_ID = "pay_test_456"


async def test_razorpay_valid_payment_signature():
    """Correctly computed payment signature returns True."""
    sig = _compute_razorpay_pay_sig(ORDER_ID, PAYMENT_ID, RAZORPAY_KEY_SECRET)
    assert verify_payment_signature(ORDER_ID, PAYMENT_ID, sig) is True


async def test_razorpay_invalid_payment_signature():
    """A fabricated payment signature is rejected."""
    assert verify_payment_signature(ORDER_ID, PAYMENT_ID, "00" * 32) is False


async def test_razorpay_payment_sig_wrong_order_id():
    """Signing with a different order ID produces a mismatch."""
    sig = _compute_razorpay_pay_sig("order_different_999", PAYMENT_ID, RAZORPAY_KEY_SECRET)
    assert verify_payment_signature(ORDER_ID, PAYMENT_ID, sig) is False


# ── Razorpay Webhook Signature ─────────────────────────────────────────────────

WEBHOOK_BODY = b'{"event":"payment.captured"}'


async def test_razorpay_webhook_valid_signature():
    """A webhook body signed with the correct secret verifies as True."""
    sig = _compute_razorpay_wh_sig(WEBHOOK_BODY, RAZORPAY_WEBHOOK_SECRET)
    assert verify_webhook_signature(WEBHOOK_BODY, sig) is True


async def test_razorpay_webhook_invalid_signature():
    """A forged webhook signature is rejected."""
    assert verify_webhook_signature(WEBHOOK_BODY, "ff" * 32) is False


async def test_razorpay_webhook_body_altered():
    """Signing the original body, then changing the body, must be detected."""
    sig = _compute_razorpay_wh_sig(WEBHOOK_BODY, RAZORPAY_WEBHOOK_SECRET)
    altered = b'{"event":"payment.failed"}'  # different event
    assert verify_webhook_signature(altered, sig) is False
