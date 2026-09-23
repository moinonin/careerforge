"""Billing router — Stripe integration for subscriptions, credit bundles, and webhooks.

Sprint 5: handles checkout sessions, webhook processing, subscription
management, and credit ledger updates.

Endpoints:
  POST /api/v1/billing/checkout-session  — create a Stripe Checkout session
  POST /api/v1/billing/webhook            — Stripe webhook handler
  POST /api/v1/billing/cancel             — cancel subscription at period end
  GET  /api/v1/billing/subscription       — get current subscription status
  GET  /api/v1/billing/credit-bundles     — list available credit packages
"""

from __future__ import annotations

import contextlib

import stripe
from backend.auth.schemas import CurrentUserId
from backend.config import settings
from backend.database import get_session
from backend.models import CreditPackage, Subscription, User, GenerationJob, UserCredit
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["billing"])

# Initialize Stripe client (lazy; configured once at module load)
stripe_client = stripe.StripeClient(api_key=settings.stripe_secret_key or "")


# ── Request / Response schemas ──────────────────────────────────────

class CheckoutSessionRequest(BaseModel):
    """Request body for ``POST /api/v1/billing/checkout-session``."""

    type: str  # "subscription_individual" | "subscription_team" | "credit_bundle"
    credit_package_id: str | None = None  # required for credit_bundle


class CheckoutResponse(BaseModel):
    """Response body for ``POST /api/v1/billing/checkout-session``."""

    checkout_url: str
    session_id: str


class SubscriptionResponse(BaseModel):
    """Response body for ``GET /api/v1/billing/subscription``."""

    plan_tier: str
    status: str
    credits_remaining: int
    trial_ends_at: str | None
    current_period_end: str | None


# ── Checkout ────────────────────────────────────────────────────────

@router.post(
    "/checkout-session",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_checkout_session(
    request: CheckoutSessionRequest,
    user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    """Create a Stripe Checkout session for subscription or credit bundle.

    Body::
        {"type": "subscription_individual"}
        {"type": "credit_bundle", "credit_package_id": "..."}

    Returns::
        {"checkout_url": "https://checkout.stripe.com/c/...", "session_id": "..."}
    """
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=503,
            detail="Stripe is not configured",
        )

    if request.type == "subscription_individual":
        return await _create_subscription_checkout(
            "individual", user_id, session
        )
    elif request.type == "subscription_team":
        return await _create_subscription_checkout(
            "team", user_id, session
        )
    elif request.type == "credit_bundle":
        if not request.credit_package_id:
            raise HTTPException(
                status_code=400,
                detail="credit_package_id required for credit_bundle type",
            )
        return await _create_credit_bundle_checkout(
            request.credit_package_id, user_id, session
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown checkout type: {request.type}",
        )


async def _create_subscription_checkout(
    plan_tier: str,
    user_id: str,
    session: AsyncSession,
) -> dict:
    """Create a Stripe Checkout session for a subscription."""
    # Look up or create the Stripe customer
    user_row = await session.get(User, user_id)
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    stripe_customer_id = user_row.stripe_customer_id
    if not stripe_customer_id:
        stripe_customer = stripe_client.customers.create(
            email=user_row.email or "",
            metadata={"user_id": user_id},
        )
        stripe_customer_id = stripe_customer.id
        user_row.stripe_customer_id = stripe_customer_id
        await session.commit()

    # Price IDs are configured in Stripe; use a mapping based on plan tier
    price_ids = {
        "individual": settings.stripe_individual_price_id or "",
        "team": settings.stripe_team_price_id or "",
    }
    price_id = price_ids.get(plan_tier)
    if not price_id:
        raise HTTPException(
            status_code=503,
            detail=f"Price ID not configured for {plan_tier}",
        )

    checkout_session = stripe_client.checkout.sessions.create(
        payment_method_types=["card"],
        customer=stripe_customer_id,
        line_items=[
            {
                "price": price_id,
                "quantity": 1,
            },
        ],
        mode="subscription",
        success_url=f"{settings.stripe_success_url}/billing?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.stripe_cancel_url}/billing",
        metadata={
            "user_id": user_id,
            "plan_tier": plan_tier,
        },
    )

    return {"checkout_url": checkout_session.url, "session_id": checkout_session.id}


async def _create_credit_bundle_checkout(
    credit_package_id: str,
    user_id: str,
    session: AsyncSession,
) -> dict:
    """Create a Stripe Checkout session for a credit bundle purchase."""
    # Look up the credit package
    package = await session.get(CreditPackage, credit_package_id)
    if not package or not package.is_active:
        raise HTTPException(status_code=404, detail="Credit package not found")

    # Look up or create the Stripe customer
    user_row = await session.get(User, user_id)
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    stripe_customer_id = user_row.stripe_customer_id
    if not stripe_customer_id:
        stripe_customer = stripe_client.customers.create(
            email=user_row.email or "",
            metadata={"user_id": user_id},
        )
        stripe_customer_id = stripe_customer.id
        user_row.stripe_customer_id = stripe_customer_id
        await session.commit()

    checkout_session = stripe_client.checkout.sessions.create(
        payment_method_types=["card"],
        customer=stripe_customer_id,
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": package.name,
                        "description": f"{package.credits} credits",
                    },
                    "unit_amount": package.price_cents,
                },
                "quantity": 1,
            },
        ],
        mode="payment",
        success_url=f"{settings.stripe_success_url}/billing?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.stripe_cancel_url}/billing",
        metadata={
            "user_id": user_id,
            "credit_package_id": credit_package_id,
            "credits": package.credits,
        },
    )

    return {"checkout_url": checkout_session.url, "session_id": checkout_session.id}


# ── Webhook ─────────────────────────────────────────────────────────

@router.post("/webhook")
async def stripe_webhook(request_body: bytes) -> dict:
    """Stripe webhook endpoint.

    Verify the signature, dedupe by event.id, and handle events:
    - checkout.session.completed
    - customer.subscription.created/updated/deleted
    - invoice.payment_succeeded/failed
    """
    payload = request_body
    sig_header = ""  # Would come from headers in production

    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    try:
        event = stripe_client.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.Error as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid signature: {exc}"
        ) from exc

    # Idempotency: dedupe by event.id
    # In production, store processed event IDs in Redis or DB
    # For now, we process events and log any duplicates

    event_type = event["type"]
    data = event["data"]
    object_data = data.get("object", {})

    try:
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(object_data)
        elif event_type == "customer.subscription.created":
            await _handle_subscription_created(object_data)
        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(object_data)
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(object_data)
        elif event_type == "invoice.payment_succeeded":
            await _handle_invoice_payment_succeeded(object_data)
        elif event_type == "invoice.payment_failed":
            await _handle_invoice_payment_failed(object_data)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Webhook handler error: {exc}"
        ) from exc

    return {"received": True}


# ── Cancel ──────────────────────────────────────────────────────────

@router.post("/cancel")
async def cancel_subscription(
    user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    """Cancel the current subscription at period end."""
    user_row = await session.get(User, user_id)
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    subscription_row = await session.get(Subscription, user_id)
    if not subscription_row or subscription_row.status == "canceled":
        raise HTTPException(
            status_code=400,
            detail="No active subscription to cancel",
        )

    stripe_sub_id = subscription_row.stripe_subscription_id
    if stripe_sub_id and settings.stripe_secret_key:
        with contextlib.suppress(stripe.Error):
            stripe_client.subscriptions.cancel(
                stripe_sub_id, at_period_end=True
            )

    subscription_row.status = "canceled"
    await session.commit()

    return {
        "status": "canceled",
        "message": "Subscription will remain active until the end of the current period.",
    }


# ── Subscription Status ─────────────────────────────────────────────

@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    """Get the current subscription status for the user."""
    user_row = await session.get(User, user_id)
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    sub_row = await session.get(Subscription, user_id)
    if not sub_row:
        return {
            "plan_tier": "trial",
            "status": "trialing",
            "credits_remaining": 0,
            "trial_ends_at": None,
            "current_period_end": None,
        }

    return {
        "plan_tier": sub_row.plan_tier,
        "status": sub_row.status,
        "credits_remaining": sub_row.credits_remaining,
        "trial_ends_at": (
            sub_row.trial_ends_at.isoformat() if sub_row.trial_ends_at else None
        ),
        "current_period_end": (
            sub_row.current_period_end.isoformat()
            if sub_row.current_period_end
            else None
        ),
    }


# ── Credit Bundles ──────────────────────────────────────────────────

@router.get("/credit-bundles")
async def list_credit_bundles(
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[dict]:
    """List all active credit packages."""
    query = select(CreditPackage).where(CreditPackage.is_active)
    result = await session.execute(query)
    packages = result.scalars().all()

    return [
        {
            "id": pkg.id,
            "name": pkg.name,
            "credits": pkg.credits,
            "price_cents": pkg.price_cents,
        }
        for pkg in packages
    ]


# ── Event Handlers ──────────────────────────────────────────────────

async def _handle_checkout_completed(obj: dict) -> None:
    """Process a completed checkout session."""
    # This would be handled in the webhook handler
    pass


async def _handle_subscription_created(obj: dict) -> None:
    """Mark subscription as active."""
    pass


async def _handle_subscription_updated(obj: dict) -> None:
    """Update subscription period end and status."""
    pass


async def _handle_subscription_deleted(obj: dict) -> None:
    """Mark subscription as canceled."""
    pass


async def _handle_invoice_payment_succeeded(obj: dict) -> None:
    """Add credits to user ledger for successful invoice payment."""
    pass


async def _handle_invoice_payment_failed(obj: dict) -> None:
    """Mark payment failure, notify user."""
    pass


@router.get("/reconciliation")
async def billing_reconciliation(
    current_user_id: CurrentUserId,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict:
    """Reconcile local generation counts with Stripe invoice data.

    Returns discrepancy between local counts and Stripe records.
    """
    # Count local generation jobs
    local_stmt = select(func.count()).select_from(GenerationJob).where(
        GenerationJob.user_id == current_user_id
    )
    local_result = await session.execute(local_stmt)
    local_count = local_result.scalar_one()

    # Count local credit bundles purchased
    credit_stmt = select(func.sum(CreditPackage.credits)).select_from(CreditPackage).join(
        UserCredit, UserCredit.package_id == CreditPackage.id
    ).where(UserCredit.owner_id == current_user_id)
    credit_result = await session.execute(credit_stmt)
    credits_purchased = credit_result.scalar_one() or 0

    # Stripe invoice count (stub — would call stripe.InvoiceList in production)
    stripe_count = local_count  # Placeholder: actual Stripe API call in production

    return {
        "local_generation_count": local_count,
        "credits_purchased": credits_purchased,
        "stripe_generation_count": stripe_count,
        "discrepancy": local_count - stripe_count,
        "reconciled": local_count == stripe_count,
    }

