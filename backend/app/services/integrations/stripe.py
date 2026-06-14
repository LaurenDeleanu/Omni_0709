import logging
import stripe
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class StripeIntegration:

    @staticmethod
    async def create_checkout_session(
        tenant_id: str,
        customer_email: str,
        tier: str,
        success_url: str,
        cancel_url: str,
        customer_id: Optional[str] = None,
        stripe_customer_id: Optional[str] = None,
    ) -> str:
        stripe.api_key = settings.STRIPE_SECRET_KEY

        price_id = settings.STRIPE_PRICE_IDS.get(tier.upper())
        if not price_id:
            raise ValueError(f"No Stripe price ID configured for tier: {tier}")

        customer_kwargs = {}
        if stripe_customer_id:
            customer_kwargs["customer"] = stripe_customer_id
        else:
            customer_kwargs["customer_creation"] = "always"
            customer_kwargs["customer_email"] = customer_email

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=tenant_id,
            metadata={"tier": tier.upper(), "tenant_id": tenant_id},
            **customer_kwargs,
        )

        logger.info(f"Stripe checkout session created: {session.id} for tenant {tenant_id}, tier {tier}")
        return session.url

    @staticmethod
    async def create_debt_payment_session(
        tenant_id: str,
        customer_email: str,
        amount_cents: int,
        success_url: str,
        cancel_url: str,
        stripe_customer_id: Optional[str] = None,
    ) -> str:
        stripe.api_key = settings.STRIPE_SECRET_KEY

        customer_kwargs = {}
        if stripe_customer_id:
            customer_kwargs["customer"] = stripe_customer_id
        else:
            customer_kwargs["customer_creation"] = "always"
            customer_kwargs["customer_email"] = customer_email

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "Debt Payment"},
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=tenant_id,
            metadata={"tenant_id": tenant_id, "type": "debt_payment"},
            **customer_kwargs,
        )

        logger.info(f"Stripe debt payment session created: {session.id} for tenant {tenant_id}")
        return session.url

    @staticmethod
    async def create_portal_session(
        customer_id: str,
        return_url: str,
    ) -> str:
        stripe.api_key = settings.STRIPE_SECRET_KEY

        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )

        logger.info(f"Stripe portal session created: {session.id} for customer {customer_id}")
        return session.url

    @staticmethod
    async def handle_webhook(payload: bytes, sig_header: str) -> Dict[str, Any]:
        stripe.api_key = settings.STRIPE_SECRET_KEY

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError as e:
            logger.warning(f"Stripe webhook signature verification failed: {e}")
            raise ValueError("Invalid Stripe webhook signature")
        except ValueError as e:
            logger.warning(f"Stripe webhook invalid payload: {e}")
            raise

        logger.info(f"Stripe webhook received: {event.type}")
        return event

    @staticmethod
    async def cancel_subscription(subscription_id: str) -> bool:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            stripe.Subscription.delete(subscription_id)
            logger.info(f"Stripe subscription cancelled: {subscription_id}")
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription {subscription_id}: {e}")
            return False
