"""
Stripe webhook handler for subscription events.
"""

from fastapi import APIRouter, Header, HTTPException, Request, status
from loguru import logger
import stripe

from app.config import settings
from app.database import get_db
from app.models import PlanTier, ZLUser

router = APIRouter()

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

PLAN_MAP = {
    settings.STRIPE_PRICE_STARTER: PlanTier.STARTER,
    settings.STRIPE_PRICE_GROWTH: PlanTier.GROWTH,
    settings.STRIPE_PRICE_PRO: PlanTier.PRO,
    settings.STRIPE_PRICE_AGENCY: PlanTier.AGENCY,
}

PLAN_LIMITS = {
    PlanTier.FREE: 25,
    PlanTier.STARTER: 750,
    PlanTier.GROWTH: 3000,
    PlanTier.PRO: 10000,
    PlanTier.AGENCY: 999999,
}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(default=None, alias="Stripe-Signature"),
):
    """Handle Stripe webhook events for subscriptions."""
    payload = await request.body()

    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("STRIPE_WEBHOOK_SECRET not set — skipping signature verification")
        # In dev, allow unsigned webhooks
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

    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})
    logger.info(f"Stripe webhook received: {event_type}")

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data)
    elif event_type == "invoice.payment_succeeded":
        await _handle_invoice_paid(data)
    elif event_type == "invoice.payment_failed":
        await _handle_invoice_failed(data)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_cancelled(data)

    return {"status": "ok"}


async def _handle_checkout_completed(data: dict) -> None:
    """Activate subscription after successful checkout."""
    customer_id = data.get("customer")
    subscription_id = data.get("subscription")
    metadata = data.get("metadata", {})
    user_id = metadata.get("user_id")

    if not user_id:
        logger.warning("Checkout session missing user_id in metadata")
        return

    async for db in get_db():
        user = await db.get(ZLUser, user_id)
        if not user:
            logger.warning(f"User {user_id} not found for Stripe checkout")
            return

        user.stripe_customer_id = customer_id
        user.stripe_subscription_id = subscription_id
        user.billing_status = "active"
        await db.commit()
        logger.info(f"Activated subscription for user {user_id}")
        break


async def _handle_invoice_paid(data: dict) -> None:
    """Update plan tier when invoice is paid."""
    subscription_id = data.get("subscription")
    lines = data.get("lines", {}).get("data", [])
    if not lines:
        return

    price_id = lines[0].get("price", {}).get("id")
    plan = PLAN_MAP.get(price_id)
    if not plan:
        logger.warning(f"Unknown Stripe price ID: {price_id}")
        return

    async for db in get_db():
        from sqlalchemy import select
        result = await db.execute(
            select(ZLUser).where(ZLUser.stripe_subscription_id == subscription_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            logger.warning(f"No user found for subscription {subscription_id}")
            return

        user.plan = plan
        user.leads_limit = PLAN_LIMITS[plan]
        user.billing_status = "active"
        await db.commit()
        logger.info(f"Updated user {user.id} to plan {plan.value}")
        break


async def _handle_invoice_failed(data: dict) -> None:
    """Mark billing as failed."""
    subscription_id = data.get("subscription")
    async for db in get_db():
        from sqlalchemy import select
        result = await db.execute(
            select(ZLUser).where(ZLUser.stripe_subscription_id == subscription_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.billing_status = "past_due"
            await db.commit()
            logger.info(f"User {user.id} billing marked past_due")
        break


async def _handle_subscription_cancelled(data: dict) -> None:
    """Downgrade to free on cancellation."""
    subscription_id = data.get("id")
    async for db in get_db():
        from sqlalchemy import select
        result = await db.execute(
            select(ZLUser).where(ZLUser.stripe_subscription_id == subscription_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.plan = PlanTier.FREE
            user.leads_limit = PLAN_LIMITS[PlanTier.FREE]
            user.stripe_subscription_id = None
            user.billing_status = "cancelled"
            await db.commit()
            logger.info(f"User {user.id} downgraded to free after cancellation")
        break
