from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.api.dependencies import get_tenant_db, get_global_db, require_roles
from app.models.tenant import Tenant
from app.models.user import User
from app.services.llm_router import encrypt_key, decrypt_key
from app.services.api_key_manager import generate_api_key, list_user_keys, revoke_api_key, rotate_api_key
from app.services.usage_quotas import get_tenant_quota_status, record_agent_run
from app.services.quota_alerts import check_and_alert_quotas
from app.services.integrations.stripe import StripeIntegration

router = APIRouter()

# --- Pydantic Schemas ---
class BillingSettingsUpdate(BaseModel):
    customOpenAiKey: Optional[str] = None
    customGeminiKey: Optional[str] = None
    customOpenRouterKey: Optional[str] = None
    customAnthropicKey: Optional[str] = None
    customGrokKey: Optional[str] = None
    customGroqKey: Optional[str] = None

class CheckoutPayload(BaseModel):
    action: str  # "upgrade" | "pay_debt" | "portal"
    tier: Optional[str] = None
    amountToPay: Optional[float] = None

# --- Routes ---

@router.get("/settings")
async def get_billing_settings(
    db: AsyncSession = Depends(get_tenant_db),
    global_db: AsyncSession = Depends(get_global_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Obtiene la configuración de facturación, saldo deudor del usuario y las API keys enmascaradas.
    """
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id") or current_user.get("tenant_id") or "acme_corp"
    current_user_email = current_user.get("email") or current_user.get("sub", "").split("|")[-1]
    
    # 1. Obtener Tenant (Global DB)
    tenant_res = await global_db.execute(select(Tenant).where(Tenant.schema_name == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
        
    # 2. Obtener User (Tenant DB)
    user_res = await db.execute(select(User).where(User.email == current_user_email))
    user = user_res.scalar_one_or_none()
    
    current_debt = user.current_debt if user else 0.0
    
    # Enmascarar las claves antes de retornar
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
async def update_billing_settings(
    payload: BillingSettingsUpdate,
    global_db: AsyncSession = Depends(get_global_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Actualiza las llaves de API personalizadas del tenant, cifrándolas de forma segura.
    """
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id") or current_user.get("tenant_id") or "acme_corp"
    
    tenant_res = await global_db.execute(select(Tenant).where(Tenant.schema_name == tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
        
    # Cifrar y guardar si no es enmascarado
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
async def checkout_payment(
    payload: CheckoutPayload,
    db: AsyncSession = Depends(get_tenant_db),
    global_db: AsyncSession = Depends(get_global_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Simula la pasarela de pagos de Stripe.
    Aplica los cambios directamente en la base de datos de forma transaccional.
    """
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id") or current_user.get("tenant_id") or "acme_corp"
    current_user_email = current_user.get("email") or current_user.get("sub", "").split("|")[-1]
    
    if payload.action == "pay_debt":
        # Mock Stripe session for debt
        url = await StripeIntegration.create_checkout_session(tenant_id, "debt", "http://localhost:3000/dashboard/settings?debt=paid", "http://localhost:3000/dashboard/settings?debt=cancel")
        return {"url": url}
            
    elif payload.action == "upgrade" and payload.tier:
        # Mock Stripe session for upgrade
        url = await StripeIntegration.create_checkout_session(tenant_id, payload.tier.upper(), f"http://localhost:3000/dashboard/settings?upgrade=success&tier={payload.tier.upper()}", "http://localhost:3000/dashboard/settings")
        return {"url": url}
            
    elif payload.action == "portal":
        return {"url": "/dashboard/settings?portal=open"}
        
    raise HTTPException(status_code=400, detail="Acción de checkout no válida")


@router.post("/webhook")
async def stripe_webhook(request: Request, global_db: AsyncSession = Depends(get_global_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    
    event = await StripeIntegration.handle_webhook(payload, sig_header)
    
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        tenant_id = session.get("client_reference_id")
        # Find tenant and update tier/debt
        if tenant_id:
            tenant_res = await global_db.execute(select(Tenant).where(Tenant.schema_name == tenant_id))
            tenant = tenant_res.scalar_one_or_none()
            if tenant:
                # Mock update tier based on some internal logic mapping
                # For now, just mark the webhook as received
                pass
                await global_db.commit()
    
    return {"status": "success"}


class ApiKeyCreate(BaseModel):
    label: str = ""
    scopes: list[str] = []


@router.post("/api-keys", status_code=status.HTTP_201_CREATED)
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
async def rotate_api_key_endpoint(
    key_hash: str,
    _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    result = rotate_api_key(key_hash)
    if not result:
        raise HTTPException(status_code=404, detail="API key not found")
    return result
