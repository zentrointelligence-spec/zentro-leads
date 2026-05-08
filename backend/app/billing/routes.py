"""
Billing routes — Stripe (card) + Billplz FPX (Malaysia) + Razorpay UPI (India).

Stripe endpoints:
  POST /billing/checkout          — create Stripe Checkout session
  POST /billing/webhook           — Stripe webhook handler

Billplz FPX endpoints:
  POST /billing/checkout/fpx      — create Billplz bill, return payment URL
  POST /billing/billplz/callback  — server-to-server callback (no auth)
  GET  /billing/billplz/redirect  — browser redirect after FPX payment

Razorpay UPI endpoints:
  POST /billing/checkout/upi      — create Razorpay order, return order details
  POST /billing/razorpay/verify   — verify payment signature, activate plan
  POST /billing/razorpay/webhook  — server-to-server webhook (no auth)
"""

from __future__ import annotations

import asyncio
from typing import Literal, Optional

import stripe
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from loguru import logger
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import get_current_user
from app.billing.billplz_client import create_bill, get_bill, verify_x_signature
from app.billing.razorpay_client import (
    create_order as razorpay_create_order,
    verify_payment_signature,
    verify_webhook_signature,
)
from app.config import settings
from app.database import get_db
from app.models import PlanTier, ZLUser

router = APIRouter()

# ── Stripe client ─────────────────────────────────────────────────────────────

stripe.api_key = settings.STRIPE_SECRET_KEY

# ── Constants ─────────────────────────────────────────────────────────────────

# Maps Stripe price IDs → internal plan tier (used by invoice webhook)
PRICE_TO_PLAN: dict[str, PlanTier] = {
    settings.STRIPE_PRICE_STARTER: PlanTier.STARTER,
    settings.STRIPE_PRICE_GROWTH:  PlanTier.GROWTH,
    settings.STRIPE_PRICE_PRO:     PlanTier.PRO,
    settings.STRIPE_PRICE_AGENCY:  PlanTier.AGENCY,
}

# Maps plan name → Stripe price ID (used by checkout)
PLAN_TO_PRICE: dict[str, str] = {
    "starter": settings.STRIPE_PRICE_STARTER,
    "growth":  settings.STRIPE_PRICE_GROWTH,
    "pro":     settings.STRIPE_PRICE_PRO,
    "agency":  settings.STRIPE_PRICE_AGENCY,
}

# Maps plan tier → monthly lead limit
PLAN_LIMITS: dict[PlanTier, int] = {
    PlanTier.FREE:    25,
    PlanTier.STARTER: 750,
    PlanTier.GROWTH:  3000,
    PlanTier.PRO:     10000,
    PlanTier.AGENCY:  999999,
}

# Maps plan name string → PlanTier (used in webhook metadata)
NAME_TO_TIER: dict[str, PlanTier] = {
    "starter": PlanTier.STARTER,
    "growth":  PlanTier.GROWTH,
    "pro":     PlanTier.PRO,
    "agency":  PlanTier.AGENCY,
}

# ── Billplz FPX pricing (in sen — RM × 100) ────────────────────────────────────
# Prices are RM-equivalent of the USD plans for Malaysian market
FPX_PRICES: dict[str, int] = {
    "starter": 14900,   # RM 149.00
    "growth":  29900,   # RM 299.00
    "pro":     49900,   # RM 499.00
    "agency":  99900,   # RM 999.00
}

FPX_DESCRIPTIONS: dict[str, str] = {
    "starter": "Zentro Leads Starter — 750 leads/month",
    "growth":  "Zentro Leads Growth — 3,000 leads/month",
    "pro":     "Zentro Leads Pro — 10,000 leads/month",
    "agency":  "Zentro Leads Agency — Unlimited leads",
}

# ── Razorpay UPI pricing (in paise — ₹ × 100) ─────────────────────────────────
# INR-equivalent of plan tiers for Indian market
UPI_PRICES: dict[str, int] = {
    "starter": 249900,   # ₹2,499
    "growth":  499900,   # ₹4,999
    "pro":     799900,   # ₹7,999
    "agency":  1499900,  # ₹14,999
}

UPI_DESCRIPTIONS: dict[str, str] = {
    "starter": "Zentro Leads Starter — 750 leads/month",
    "growth":  "Zentro Leads Growth — 3,000 leads/month",
    "pro":     "Zentro Leads Pro — 10,000 leads/month",
    "agency":  "Zentro Leads Agency — Unlimited leads",
}


# ── Auth dependency ───────────────────────────────────────────────────────────

async def get_current_user_dep(
    zentro_session: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> ZLUser:
    """Dependency wrapper that injects db into get_current_user."""
    return await get_current_user(zentro_session=zentro_session, db=db)


# ── Schemas ───────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    """Checkout session creation payload."""
    plan: Literal["starter", "growth", "pro", "agency"]


class CheckoutResponse(BaseModel):
    """URL to redirect the user to Stripe Checkout."""
    checkout_url: str


class FpxCheckoutRequest(BaseModel):
    """FPX checkout payload — plan + Malaysian mobile number."""
    plan: Literal["starter", "growth", "pro", "agency"]
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Strip whitespace/dashes; reject obviously invalid numbers."""
        cleaned = v.strip().replace(" ", "").replace("-", "")
        if len(cleaned) < 9:
            raise ValueError("Phone number is too short")
        return cleaned


class FpxCheckoutResponse(BaseModel):
    """Billplz payment URL — frontend redirects user here."""
    fpx_url: str
    bill_id: str


class UpiCheckoutRequest(BaseModel):
    """UPI checkout payload — plan name only (no phone needed for Razorpay)."""
    plan: Literal["starter", "growth", "pro", "agency"]


class UpiCheckoutResponse(BaseModel):
    """Razorpay order details — frontend opens Razorpay.js modal with these."""
    order_id:     str
    amount:       int
    currency:     str
    razorpay_key: str


class RazorpayVerifyRequest(BaseModel):
    """Payment signature verification payload sent by frontend after checkout."""
    order_id:   str
    payment_id: str
    signature:  str
    plan:       Literal["starter", "growth", "pro", "agency"]


class RazorpayVerifyResponse(BaseModel):
    """Result of payment signature verification."""
    success: bool
    plan:    str


# ── POST /api/v1/billing/checkout ─────────────────────────────────────────────

@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    summary="Create a Stripe Checkout session for a subscription upgrade",
)
async def create_checkout_session(
    body: CheckoutRequest,
    current_user: ZLUser = Depends(get_current_user_dep),
) -> CheckoutResponse:
    """
    Create a Stripe Checkout session for the requested plan.

    Returns a ``checkout_url`` the frontend should redirect the browser to.
    The session carries ``user_id`` and ``plan`` in metadata so the webhook
    can immediately activate the right plan on completion.
    """
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured. Set STRIPE_SECRET_KEY in backend/.env",
        )

    price_id = PLAN_TO_PRICE.get(body.plan, "")
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Stripe price ID for plan '{body.plan}' is not configured. "
                   "Set STRIPE_PRICE_{PLAN} in backend/.env",
        )

    success_url = (
        f"{settings.FRONTEND_URL}/dashboard/settings"
        f"?tab=billing&billing=success&plan={body.plan}"
    )
    cancel_url = (
        f"{settings.FRONTEND_URL}/dashboard/settings"
        f"?tab=billing&billing=cancelled"
    )

    try:
        session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            mode="subscription",
            payment_method_types=["card"],
            customer_email=str(current_user.email),
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": str(current_user.id),
                "plan":    body.plan,
            },
        )
    except stripe.error.StripeError as exc:
        logger.error(f"Stripe checkout creation failed for user {current_user.id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not create checkout session. Please try again.",
        )

    logger.info(
        f"Stripe checkout session created for user {current_user.id} "
        f"→ plan={body.plan} session={session.id}"
    )
    return CheckoutResponse(checkout_url=session.url)


# ── POST /api/v1/billing/webhook ──────────────────────────────────────────────

@router.post("/webhook", summary="Receive Stripe webhook events")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(default=None, alias="Stripe-Signature"),
) -> dict:
    """Handle Stripe webhook events for subscriptions."""
    payload = await request.body()

    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("STRIPE_WEBHOOK_SECRET not set — skipping signature verification")
        try:
            event = stripe.Event.construct_from(payload, stripe.api_key)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}")
    else:
        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError as exc:
            logger.warning(f"Stripe signature verification failed: {exc}")
            raise HTTPException(status_code=400, detail="Invalid signature")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}")

    event_type: str = event.get("type", "")
    data: dict = event.get("data", {}).get("object", {})
    logger.info(f"Stripe webhook received: {event_type}")

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data)
    elif event_type == "invoice.payment_succeeded":
        await _handle_invoice_paid(data)
    elif event_type == "invoice.payment_failed":
        await _handle_invoice_failed(data)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_cancelled(data)
    else:
        logger.debug(f"Unhandled Stripe event type: {event_type}")

    return {"status": "ok"}


# ── Webhook handlers ──────────────────────────────────────────────────────────


async def _handle_checkout_completed(data: dict) -> None:
    """
    Activate subscription immediately after successful checkout.

    We store customer + subscription IDs and immediately apply the plan tier
    from session metadata so the user doesn't have to wait for the
    invoice.payment_succeeded event.
    """
    customer_id     = data.get("customer")
    subscription_id = data.get("subscription")
    metadata        = data.get("metadata") or {}
    user_id         = metadata.get("user_id")
    plan_name       = metadata.get("plan", "").lower()

    if not user_id:
        logger.warning("checkout.session.completed: missing user_id in metadata")
        return

    tier = NAME_TO_TIER.get(plan_name)

    async for db in get_db():
        user = await db.get(ZLUser, user_id)
        if not user:
            logger.warning(f"checkout.session.completed: user {user_id} not found")
            return

        user.stripe_customer_id     = customer_id
        user.stripe_subscription_id = subscription_id
        user.billing_status         = "active"

        if tier is not None:
            user.plan         = tier
            user.leads_limit  = PLAN_LIMITS[tier]
            logger.info(f"checkout.session.completed: user {user_id} upgraded → {plan_name}")

        await db.commit()
        break


async def _handle_invoice_paid(data: dict) -> None:
    """
    Keep plan tier in sync on every successful renewal invoice.

    Acts as the source of truth for plan tier on recurring payments since
    checkout.session.completed only fires once at the initial purchase.
    """
    subscription_id = data.get("subscription")
    lines = data.get("lines", {}).get("data", [])
    if not lines:
        return

    price_id = lines[0].get("price", {}).get("id")
    plan     = PRICE_TO_PLAN.get(price_id)
    if not plan:
        logger.warning(f"invoice.payment_succeeded: unknown price ID {price_id!r}")
        return

    async for db in get_db():
        result = await db.execute(
            select(ZLUser).where(ZLUser.stripe_subscription_id == subscription_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            logger.warning(f"invoice.payment_succeeded: no user for subscription {subscription_id}")
            return

        user.plan           = plan
        user.leads_limit    = PLAN_LIMITS[plan]
        user.billing_status = "active"
        await db.commit()
        logger.info(f"invoice.payment_succeeded: user {user.id} → {plan.value}")
        break


async def _handle_invoice_failed(data: dict) -> None:
    """Mark billing as past_due when a renewal payment fails."""
    subscription_id = data.get("subscription")
    async for db in get_db():
        result = await db.execute(
            select(ZLUser).where(ZLUser.stripe_subscription_id == subscription_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.billing_status = "past_due"
            await db.commit()
            logger.info(f"invoice.payment_failed: user {user.id} marked past_due")
        break


async def _handle_subscription_cancelled(data: dict) -> None:
    """Downgrade user to Free plan on subscription cancellation."""
    subscription_id = data.get("id")
    async for db in get_db():
        result = await db.execute(
            select(ZLUser).where(ZLUser.stripe_subscription_id == subscription_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.plan                   = PlanTier.FREE
            user.leads_limit            = PLAN_LIMITS[PlanTier.FREE]
            user.stripe_subscription_id = None
            user.billing_status         = "cancelled"
            await db.commit()
            logger.info(f"customer.subscription.deleted: user {user.id} downgraded to free")
        break


# ═══════════════════════════════════════════════════════════════════════════════
# Billplz FPX endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/checkout/fpx",
    response_model=FpxCheckoutResponse,
    summary="Create a Billplz FPX bill for Malaysian customers",
)
async def create_fpx_checkout(
    body: FpxCheckoutRequest,
    current_user: ZLUser = Depends(get_current_user_dep),
) -> FpxCheckoutResponse:
    """
    Create a Billplz FPX bill for the requested plan.

    Returns ``fpx_url`` — the frontend should redirect the browser to this URL
    so the customer can complete FPX online banking payment.

    The phone number is required by Billplz for FPX and SMS receipt.
    """
    if not settings.BILLPLZ_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FPX payments are not configured. Set BILLPLZ_API_KEY in backend/.env",
        )

    amount_sen = FPX_PRICES.get(body.plan)
    if not amount_sen:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown plan '{body.plan}'",
        )

    redirect_url = (
        f"{settings.BACKEND_URL}/api/v1/billing/billplz/redirect"
    )
    callback_url = (
        f"{settings.BACKEND_URL}/api/v1/billing/billplz/callback"
    )

    try:
        bill = await create_bill(
            name         = str(current_user.full_name),
            email        = str(current_user.email),
            phone        = body.phone,
            amount_cents = amount_sen,
            description  = FPX_DESCRIPTIONS.get(body.plan, f"Zentro Leads {body.plan.capitalize()}"),
            user_id      = str(current_user.id),
            plan         = body.plan,
            redirect_url = redirect_url,
            callback_url = callback_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error(f"[fpx] Bill creation error for user {current_user.id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not create FPX payment. Please try again.",
        )

    logger.info(
        f"[fpx] Bill created for user={current_user.id} "
        f"plan={body.plan} bill_id={bill['bill_id']}"
    )
    return FpxCheckoutResponse(fpx_url=bill["url"], bill_id=bill["bill_id"])


@router.post(
    "/billplz/callback",
    summary="Billplz server-to-server callback — no auth required",
    status_code=200,
)
async def billplz_callback(request: Request) -> dict:
    """
    Receive server-to-server FPX payment result from Billplz.

    Always returns HTTP 200 — Billplz retries on any non-200 response
    (up to 5 attempts over 24 hours).

    Security: X-Signature in the POST body is verified with HMAC-SHA256
    before any DB changes are made.
    """
    # Billplz sends application/x-www-form-urlencoded
    try:
        form = await request.form()
        data = dict(form)
    except Exception as exc:
        logger.error(f"[fpx callback] Failed to parse form body: {exc}")
        return {"status": "ok"}  # Return 200 regardless

    bill_id     = data.get("id", "")
    paid_str    = str(data.get("paid", "false")).lower()
    x_signature = str(data.get("x_signature", ""))
    user_id     = str(data.get("reference_1", ""))
    plan_name   = str(data.get("reference_2", "")).lower()

    logger.info(
        f"[fpx callback] bill_id={bill_id} paid={paid_str} "
        f"user_id={user_id} plan={plan_name}"
    )

    # ── Verify X-Signature ────────────────────────────────────────────────────
    if not verify_x_signature(data, x_signature):
        logger.warning(f"[fpx callback] X-Signature invalid for bill {bill_id} — ignoring")
        return {"status": "ok"}

    # ── Only act on successful payments ──────────────────────────────────────
    if paid_str != "true":
        logger.info(f"[fpx callback] Bill {bill_id} not paid (paid={paid_str}) — skipping")
        return {"status": "ok"}

    if not user_id or not plan_name:
        logger.warning(f"[fpx callback] Missing user_id or plan in references for bill {bill_id}")
        return {"status": "ok"}

    tier = NAME_TO_TIER.get(plan_name)
    if tier is None:
        logger.warning(f"[fpx callback] Unknown plan '{plan_name}' for bill {bill_id}")
        return {"status": "ok"}

    # ── Activate plan in DB ───────────────────────────────────────────────────
    try:
        async for db in get_db():
            user = await db.get(ZLUser, user_id)
            if not user:
                logger.warning(f"[fpx callback] User {user_id} not found for bill {bill_id}")
                break

            user.plan           = tier
            user.leads_limit    = PLAN_LIMITS[tier]
            user.billing_status = "active"
            await db.commit()
            logger.info(
                f"[fpx callback] User {user_id} upgraded to {plan_name} via FPX "
                f"(bill={bill_id})"
            )
            break
    except Exception as exc:
        logger.error(f"[fpx callback] DB update failed for bill {bill_id}: {exc}")
        # Still return 200 — we already verified the payment; log for manual review

    return {"status": "ok"}


@router.get(
    "/billplz/redirect",
    summary="Billplz browser redirect after FPX payment",
)
async def billplz_redirect(request: Request) -> RedirectResponse:
    """
    Handle browser redirect from Billplz after FPX payment completes.

    Billplz appends ``billplz[id]``, ``billplz[paid]``, ``billplz[paid_at]``
    and ``billplz[x_signature]`` to this URL. We verify the signature and
    redirect the user to the appropriate settings page.

    This endpoint acts as a security layer between Billplz and the frontend
    — the frontend never receives unverified payment status.
    """
    params = dict(request.query_params)

    # Billplz uses bracket notation: billplz[id], billplz[paid], etc.
    # Extract the inner values and normalise to a flat dict for verification
    bz: dict[str, str] = {}
    for key, val in params.items():
        # Handle both billplz[key] and billplz_key
        if key.startswith("billplz[") and key.endswith("]"):
            inner = key[len("billplz["):-1]
            bz[f"billplz[{inner}]"] = val
        elif key.startswith("billplz_"):
            inner = key[len("billplz_"):]
            bz[f"billplz[{inner}]"] = val

    bill_id     = bz.get("billplz[id]", "")
    paid_str    = str(bz.get("billplz[paid]", "false")).lower()
    x_sig       = bz.get("billplz[x_signature]", "")

    failed_url  = (
        f"{settings.FRONTEND_URL}/dashboard/settings"
        f"?tab=billing&billing=failed"
    )
    success_url = (
        f"{settings.FRONTEND_URL}/dashboard/settings"
        f"?tab=billing&billing=success"
    )

    if not bill_id:
        logger.warning("[fpx redirect] No bill_id in redirect params")
        return RedirectResponse(url=failed_url, status_code=302)

    # Verify X-Signature using only the billplz[*] params (excluding x_signature)
    sig_data = {k: v for k, v in bz.items() if k != "billplz[x_signature]"}
    if x_sig and not verify_x_signature(sig_data, x_sig):
        logger.warning(f"[fpx redirect] X-Signature invalid for bill {bill_id}")
        return RedirectResponse(url=failed_url, status_code=302)

    if paid_str == "true":
        logger.info(f"[fpx redirect] Bill {bill_id} paid — redirecting to success")
        return RedirectResponse(url=success_url, status_code=302)

    logger.info(f"[fpx redirect] Bill {bill_id} not paid — redirecting to failed")
    return RedirectResponse(url=failed_url, status_code=302)


# ═══════════════════════════════════════════════════════════════════════════════
# Razorpay UPI endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/checkout/upi",
    response_model=UpiCheckoutResponse,
    summary="Create a Razorpay order for Indian UPI/card/NetBanking payment",
)
async def create_upi_checkout(
    body: UpiCheckoutRequest,
    current_user: ZLUser = Depends(get_current_user_dep),
) -> UpiCheckoutResponse:
    """
    Create a Razorpay order for the requested plan.

    Returns order details the frontend passes to Razorpay.js to open the
    payment modal (supports UPI, card, NetBanking, wallets).

    Flow:
      1. Frontend calls this endpoint to get an order_id + amount.
      2. Frontend loads Razorpay.js and opens the modal.
      3. User completes payment.
      4. Razorpay calls the ``handler`` callback with payment details.
      5. Frontend calls ``POST /billing/razorpay/verify`` to activate the plan.
    """
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="UPI payments are not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in backend/.env",
        )

    amount_paise = UPI_PRICES.get(body.plan)
    if not amount_paise:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown plan '{body.plan}'",
        )

    try:
        order = await razorpay_create_order(
            amount_paise = amount_paise,
            currency     = "INR",
            user_id      = str(current_user.id),
            plan         = body.plan,
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error(f"[upi] Order creation error for user {current_user.id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not create payment order. Please try again.",
        )

    logger.info(
        f"[upi] Order created for user={current_user.id} "
        f"plan={body.plan} order_id={order['order_id']}"
    )
    return UpiCheckoutResponse(
        order_id     = order["order_id"],
        amount       = order["amount"],
        currency     = order["currency"],
        razorpay_key = settings.RAZORPAY_KEY_ID,
    )


@router.post(
    "/razorpay/verify",
    response_model=RazorpayVerifyResponse,
    summary="Verify Razorpay payment signature and activate plan",
)
async def verify_razorpay_payment(
    body: RazorpayVerifyRequest,
    current_user: ZLUser = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db),
) -> RazorpayVerifyResponse:
    """
    Verify a Razorpay payment signature and activate the plan on success.

    Called by the frontend immediately after the Razorpay.js ``handler``
    callback fires with ``razorpay_payment_id``, ``razorpay_order_id``, and
    ``razorpay_signature``.

    Security: signature is HMAC-SHA256 of "{order_id}|{payment_id}" using
    RAZORPAY_KEY_SECRET — forged requests without access to the secret will fail.
    """
    is_valid = verify_payment_signature(
        order_id   = body.order_id,
        payment_id = body.payment_id,
        signature  = body.signature,
    )

    if not is_valid:
        logger.warning(
            f"[upi verify] Invalid signature for user={current_user.id} "
            f"order={body.order_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment signature verification failed. Payment not activated.",
        )

    tier = NAME_TO_TIER.get(body.plan)
    if tier is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown plan '{body.plan}'",
        )

    current_user.plan           = tier
    current_user.leads_limit    = PLAN_LIMITS[tier]
    current_user.billing_status = "active"
    await db.commit()

    logger.info(
        f"[upi verify] User {current_user.id} upgraded to {body.plan} "
        f"(order={body.order_id} payment={body.payment_id})"
    )
    return RazorpayVerifyResponse(success=True, plan=body.plan)


@router.post(
    "/razorpay/webhook",
    summary="Razorpay server-to-server webhook — no auth required",
    status_code=200,
)
async def razorpay_webhook(request: Request) -> dict:
    """
    Receive Razorpay server-to-server webhook events.

    Always returns HTTP 200 — Razorpay retries on non-200 responses.

    Handles:
      payment.captured — activates plan from order notes (user_id, plan).

    Security: X-Razorpay-Signature header is verified with HMAC-SHA256 of the
    raw request body using RAZORPAY_WEBHOOK_SECRET before any DB changes.
    """
    body_bytes = await request.body()
    signature  = request.headers.get("x-razorpay-signature", "")

    if not verify_webhook_signature(body_bytes, signature):
        logger.warning("[razorpay webhook] Signature verification failed — ignoring")
        return {"status": "ok"}

    try:
        import json as _json
        payload = _json.loads(body_bytes)
    except Exception as exc:
        logger.error(f"[razorpay webhook] Failed to parse JSON body: {exc}")
        return {"status": "ok"}

    event = payload.get("event", "")
    logger.info(f"[razorpay webhook] Received event: {event}")

    if event == "payment.captured":
        payment_entity = (
            payload.get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )
        notes    = payment_entity.get("notes", {})
        user_id  = str(notes.get("user_id", ""))
        plan_name = str(notes.get("plan", "")).lower()
        payment_id = str(payment_entity.get("id", ""))

        if not user_id or not plan_name:
            logger.warning(
                f"[razorpay webhook] Missing user_id or plan in notes "
                f"for payment {payment_id}"
            )
            return {"status": "ok"}

        tier = NAME_TO_TIER.get(plan_name)
        if tier is None:
            logger.warning(
                f"[razorpay webhook] Unknown plan '{plan_name}' "
                f"for payment {payment_id}"
            )
            return {"status": "ok"}

        try:
            async for db in get_db():
                user = await db.get(ZLUser, user_id)
                if not user:
                    logger.warning(
                        f"[razorpay webhook] User {user_id} not found "
                        f"for payment {payment_id}"
                    )
                    break

                user.plan           = tier
                user.leads_limit    = PLAN_LIMITS[tier]
                user.billing_status = "active"
                await db.commit()
                logger.info(
                    f"[razorpay webhook] User {user_id} activated plan={plan_name} "
                    f"via webhook (payment={payment_id})"
                )
                break
        except Exception as exc:
            logger.error(
                f"[razorpay webhook] DB update failed for payment {payment_id}: {exc}"
            )

    return {"status": "ok"}
