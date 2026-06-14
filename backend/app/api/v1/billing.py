import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.dependencies import get_tenant_db, get_global_db, require_roles, get_current_user
from app.models.tenant import Tenant
from app.models.user import User
from app.models.invoice import CustomerInvoice
from app.services.llm_router import encrypt_key, decrypt_key
from app.services.api_key_manager import generate_api_key, list_user_keys, revoke_api_key, rotate_api_key
from app.services.usage_quotas import get_tenant_quota_status, record_agent_run
from app.services.quota_alerts import check_and_alert_quotas
from app.services.integrations.stripe import StripeIntegration
from app.services.invoice_pdf import generate_invoice_pdf
from app.core.config import settings

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


class BillingSettingsUpdate(BaseModel):
    customOpenAiKey: Optional[str] = None
    customGeminiKey: Optional[str] = None
    customOpenRouterKey: Optional[str] = None
    customAnthropicKey: Optional[str] = None
    customGrokKey: Optional[str] = None
    customGroqKey: Optional[str] = None


class CheckoutPayload(BaseModel):
    action: str
    tier: Optional[str] = None
    amountToPay: Optional[float] = None


@router.get("/settings")
async def get_billing_settings(
    db: AsyncSession = Depends(get_tenant_db),
    global_db: AsyncSession = Depends(get_global_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id") or current_user.get("tenant_id") or "acme_corp"
    current_user_email = current_user.get("email") or current_user.get("sub", "").split("|")[-1]

    tenant_res = await global_db.execute(select(Tenant).where(Tenant.schema_name == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    user_res = await db.execute(select(User).where(User.email == current_user_email))
    user = user_res.scalar_one_or_none()

    current_debt = user.current_debt if user else 0.0

    return {
        "tier": tenant.tier or "FREE",
        "currentDebt": current_debt,
        "customOpenAiKey": "********" if tenant.custom_openai_key else "",
        "customGeminiKey": "********" if tenant.custom_gemini_key else "",
        "customOpenRouterKey": "********" if tenant.custom_openrouter_key else "",
        "customAnthropicKey": "********" if tenant.custom_anthropic_key else "",
        "customGrokKey": "********" if tenant.custom_grok_key else "",
        "customGroqKey": "********" if tenant.custom_groq_key else "",
    }


@router.patch("/settings")
@limiter.limit("30/minute")
async def update_billing_settings(
    payload: BillingSettingsUpdate,
    global_db: AsyncSession = Depends(get_global_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id") or current_user.get("tenant_id") or "acme_corp"

    tenant_res = await global_db.execute(select(Tenant).where(Tenant.schema_name == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    if payload.customOpenAiKey is not None:
        if payload.customOpenAiKey != "********" and payload.customOpenAiKey != "":
            tenant.custom_openai_key = encrypt_key(payload.customOpenAiKey)
        elif payload.customOpenAiKey == "":
            tenant.custom_openai_key = None

    if payload.customGeminiKey is not None:
        if payload.customGeminiKey != "********" and payload.customGeminiKey != "":
            tenant.custom_gemini_key = encrypt_key(payload.customGeminiKey)
        elif payload.customGeminiKey == "":
            tenant.custom_gemini_key = None

    if payload.customOpenRouterKey is not None:
        if payload.customOpenRouterKey != "********" and payload.customOpenRouterKey != "":
            tenant.custom_openrouter_key = encrypt_key(payload.customOpenRouterKey)
        elif payload.customOpenRouterKey == "":
            tenant.custom_openrouter_key = None

    if payload.customAnthropicKey is not None:
        if payload.customAnthropicKey != "********" and payload.customAnthropicKey != "":
            tenant.custom_anthropic_key = encrypt_key(payload.customAnthropicKey)
        elif payload.customAnthropicKey == "":
            tenant.custom_anthropic_key = None

    if payload.customGrokKey is not None:
        if payload.customGrokKey != "********" and payload.customGrokKey != "":
            tenant.custom_grok_key = encrypt_key(payload.customGrokKey)
        elif payload.customGrokKey == "":
            tenant.custom_grok_key = None

    if payload.customGroqKey is not None:
        if payload.customGroqKey != "********" and payload.customGroqKey != "":
            tenant.custom_groq_key = encrypt_key(payload.customGroqKey)
        elif payload.customGroqKey == "":
            tenant.custom_groq_key = None

    await global_db.commit()
    return {"success": True}


@router.post("/checkout")
@limiter.limit("10/minute")
async def checkout_payment(
    payload: CheckoutPayload,
    db: AsyncSession = Depends(get_tenant_db),
    global_db: AsyncSession = Depends(get_global_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id") or current_user.get("tenant_id") or "acme_corp"
    current_user_email = current_user.get("email") or current_user.get("sub", "").split("|")[-1]

    tenant_res = await global_db.execute(select(Tenant).where(Tenant.schema_name == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    frontend_url = settings.FRONTEND_URL.rstrip("/")

    try:
        if payload.action == "pay_debt":
            amount_to_pay = payload.amountToPay or 0.0
            if amount_to_pay <= 0:
                raise HTTPException(status_code=400, detail="Invalid debt amount")

            amount_cents = int(round(amount_to_pay * 100))
            success_url = f"{frontend_url}/dashboard/settings?debt=paid"
            cancel_url = f"{frontend_url}/dashboard/settings?debt=cancel"

            url = await StripeIntegration.create_debt_payment_session(
                tenant_id=tenant_id,
                customer_email=current_user_email,
                amount_cents=amount_cents,
                success_url=success_url,
                cancel_url=cancel_url,
                stripe_customer_id=tenant.stripe_customer_id,
            )
            return {"url": url}

        elif payload.action == "upgrade" and payload.tier:
            tier_upper = payload.tier.upper()
            if tier_upper not in settings.STRIPE_PRICE_IDS:
                raise HTTPException(status_code=400, detail=f"Unsupported tier: {payload.tier}")

            success_url = f"{frontend_url}/dashboard/settings?upgrade=success&tier={tier_upper}"
            cancel_url = f"{frontend_url}/dashboard/settings"

            url = await StripeIntegration.create_checkout_session(
                tenant_id=tenant_id,
                customer_email=current_user_email,
                tier=tier_upper,
                success_url=success_url,
                cancel_url=cancel_url,
                stripe_customer_id=tenant.stripe_customer_id,
            )
            return {"url": url}

        elif payload.action == "portal":
            if not tenant.stripe_customer_id:
                raise HTTPException(status_code=400, detail="No Stripe customer found for this tenant")

            return_url = f"{frontend_url}/dashboard/settings?portal=open"
            url = await StripeIntegration.create_portal_session(
                customer_id=tenant.stripe_customer_id,
                return_url=return_url,
            )
            return {"url": url}

        raise HTTPException(status_code=400, detail="Acción de checkout no válida")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Stripe checkout error for tenant {tenant_id}")
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")


@router.post("/webhook")
async def stripe_webhook(request: Request, global_db: AsyncSession = Depends(get_global_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = await StripeIntegration.handle_webhook(payload, sig_header)
    except (ValueError, Exception) as e:
        logger.warning(f"Webhook verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    event_type = event["type"]
    event_data = event["data"]["object"]

    try:
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(event_data, global_db)

        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(event_data, global_db)

        elif event_type == "invoice.payment_failed":
            await _handle_invoice_payment_failed(event_data, global_db)

        await global_db.commit()

    except Exception as e:
        logger.exception(f"Webhook handler error for event {event_type}")
        await global_db.rollback()
        raise HTTPException(status_code=500, detail="Webhook processing error")

    return {"status": "success"}


async def _handle_checkout_completed(session: dict, global_db: AsyncSession):
    tenant_id = session.get("client_reference_id")
    if not tenant_id:
        tenant_id = session.get("metadata", {}).get("tenant_id")

    if not tenant_id:
        logger.warning("checkout.session.completed without tenant_id reference")
        return

    tenant_res = await global_db.execute(
        select(Tenant).where(Tenant.schema_name == tenant_id)
    )
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        logger.warning(f"Tenant not found for checkout completion: {tenant_id}")
        return

    stripe_customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    metadata = session.get("metadata", {})
    tier = metadata.get("tier", tenant.tier)

    if stripe_customer_id:
        tenant.stripe_customer_id = stripe_customer_id
    if subscription_id:
        tenant.subscription_id = subscription_id
    tenant.subscription_status = "active"
    tenant.subscription_tier = tier
    tenant.tier = tier

    logger.info(f"Tenant {tenant_id} upgraded to {tier} (subscription: {subscription_id})")


async def _handle_subscription_deleted(subscription: dict, global_db: AsyncSession):
    subscription_id = subscription.get("id")
    if not subscription_id:
        return

    tenant_res = await global_db.execute(
        select(Tenant).where(Tenant.subscription_id == subscription_id)
    )
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        logger.warning(f"Tenant not found for subscription {subscription_id}")
        return

    tenant.subscription_status = "canceled"
    tenant.subscription_tier = None
    tenant.tier = "FREE"

    logger.info(f"Tenant {tenant.schema_name} downgraded to FREE (subscription {subscription_id} deleted)")


async def _handle_invoice_payment_failed(invoice: dict, global_db: AsyncSession):
    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")

    if not customer_id:
        return

    if subscription_id:
        tenant_res = await global_db.execute(
            select(Tenant).where(Tenant.subscription_id == subscription_id)
        )
        tenant = tenant_res.scalar_one_or_none()
    else:
        tenant_res = await global_db.execute(
            select(Tenant).where(Tenant.stripe_customer_id == customer_id)
        )
        tenant = tenant_res.scalar_one_or_none()

    if not tenant:
        logger.warning(f"Tenant not found for failed invoice (customer: {customer_id})")
        return

    tenant.subscription_status = "past_due"

    logger.info(f"Tenant {tenant.schema_name} marked past_due (invoice payment failed)")


class ApiKeyCreate(BaseModel):
    label: str = ""
    scopes: list[str] = []


@router.post("/api-keys", status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_api_key(
    body: ApiKeyCreate,
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    user_id = current_user.get("sub", "").split("|")[-1]
    tenant_id = current_user.get("https://successcore.com/app_metadata", {}).get("tenant_id", "")
    result = generate_api_key(user_id, tenant_id, body.scopes or ["read:all"], body.label)
    return result


@router.get("/api-keys")
async def get_api_keys(
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    user_id = current_user.get("sub", "").split("|")[-1]
    return {"keys": list_user_keys(user_id)}


@router.post("/api-keys/{key_hash}/revoke")
@limiter.limit("30/minute")
async def revoke_api_key_endpoint(
    key_hash: str,
    _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    ok = revoke_api_key(key_hash)
    if not ok:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"status": "revoked"}


@router.get("/quotas")
async def get_usage_quotas(
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"])),
    db: AsyncSession = Depends(get_tenant_db),
):
    tenant_id = current_user.get("https://successcore.com/app_metadata", {}).get("tenant_id", "")
    from app.models.tenant import Tenant
    tier = "FREE"
    from app.core.database import AsyncSessionGlobal
    async with AsyncSessionGlobal() as gdb:
        t_res = await gdb.execute(select(Tenant).where(Tenant.schema_name == tenant_id))
        t = t_res.scalar_one_or_none()
        if t:
            tier = t.tier or "FREE"

    status = await get_tenant_quota_status(tenant_id, tier)
    admin_id = current_user.get("sub", "").split("|")[-1]
    await check_and_alert_quotas(db, tenant_id, tier, admin_id)
    return status


@router.post("/api-keys/{key_hash}/rotate")
@limiter.limit("30/minute")
async def rotate_api_key_endpoint(
    key_hash: str,
    _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    result = rotate_api_key(key_hash)
    if not result:
        raise HTTPException(status_code=404, detail="API key not found")
    return result


@router.get("/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(CustomerInvoice).where(CustomerInvoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id") or current_user.get("tenant_id", "")

    invoice_data = {
        "invoice_number": invoice.invoice_number,
        "date": invoice.date.isoformat() if invoice.date else "",
        "due_date": invoice.due_date.isoformat() if invoice.due_date else "",
        "currency": invoice.currency,
        "customer_name": invoice.customer_name,
        "customer_email": invoice.customer_email,
        "customer_address": invoice.customer_address or "",
        "line_items": invoice.line_items or [],
        "tax_rate": invoice.tax_rate,
        "notes": invoice.notes or "",
        "payment_terms": invoice.payment_terms or "",
    }

    pdf_bytes = await generate_invoice_pdf(invoice_data, tenant_id)

    filename = f"invoice_{invoice.invoice_number}.pdf"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=bytes(pdf_bytes), headers=headers, media_type="application/pdf")


# ── Usage-Based Billing ────────────────────────────────────────────────────────

@router.get("/usage")
async def get_tenant_usage(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.usage_billing import get_tenant_usage_summary
    tenant_id = current_user.get("tenant_id", "default")
    return await get_tenant_usage_summary(db, tenant_id, days)


@router.get("/bill")
async def get_monthly_bill(
    month: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.usage_billing import generate_monthly_bill
    tenant_id = current_user.get("tenant_id", "default")
    return await generate_monthly_bill(db, tenant_id, month)
