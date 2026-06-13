from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.api.dependencies import get_tenant_db, get_current_user, get_tenant_db_from_api_key, require_roles
from app.models.integration import UserIntegration
from typing import List, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import uuid

router = APIRouter()

def get_user_id(current_user: dict) -> str:
    sub = current_user.get("sub", "")
    return sub.split("|")[-1] if "|" in sub else sub

class IntegrationOut(BaseModel):
    id: str
    provider: str
    external_email: str | None
    sync_enabled: bool
    last_sync_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True

class CallbackIn(BaseModel):
    code: str

@router.get("", response_model=List[IntegrationOut])
async def list_integrations(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    """Listar las integraciones activas del usuario."""
    user_id = get_user_id(current_user)
    result = await db.execute(select(UserIntegration).where(UserIntegration.user_id == user_id))
    return result.scalars().all()

@router.get("/{provider}/auth-url")
async def get_auth_url(
    provider: str,
    current_user: dict = Depends(get_current_user)
):
    """Devuelve la URL de autorización OAuth2 (Mock para la fase de prototipo)."""
    if provider not in ["google", "microsoft"]:
        raise HTTPException(status_code=400, detail="Proveedor no soportado")
    
    # Mocking real OAuth flow for prototype purposes
    mock_url = f"/dashboard/settings/integrations/callback?provider={provider}&code=mock_oauth_code_12345"
    return {"auth_url": mock_url}

@router.post("/{provider}/callback")
async def oauth_callback(
    provider: str,
    payload: CallbackIn,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    """Intercambia el auth code por tokens y los guarda en la base de datos."""
    if provider not in ["google", "microsoft"]:
        raise HTTPException(status_code=400, detail="Proveedor no soportado")
    
    user_id = get_user_id(current_user)
    
    # Simulate exchanging code for tokens
    fake_access_token = f"ya29.a0AfB_{uuid.uuid4().hex}"
    fake_refresh_token = f"1//0e_{uuid.uuid4().hex}"
    fake_email = f"employee@{provider}.test.com"
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    
    # Check if exists
    result = await db.execute(
        select(UserIntegration).where(
            UserIntegration.user_id == user_id, 
            UserIntegration.provider == provider
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.access_token = fake_access_token
        existing.refresh_token = fake_refresh_token
        existing.expires_at = expires
        existing.external_email = fake_email
    else:
        new_integration = UserIntegration(
            id=uuid.uuid4().hex,
            user_id=user_id,
            provider=provider,
            external_email=fake_email,
            access_token=fake_access_token,
            refresh_token=fake_refresh_token,
            expires_at=expires,
            sync_enabled=True
        )
        db.add(new_integration)
        
    await db.commit()
    return {"message": f"Conectado exitosamente con {provider}"}

@router.delete("/{provider}")
async def disconnect_integration(
    provider: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    """Revoca tokens y elimina la integración."""
    user_id = get_user_id(current_user)
    await db.execute(
        delete(UserIntegration).where(
            UserIntegration.user_id == user_id,
            UserIntegration.provider == provider
        )
    )
    await db.commit()
    return {"message": f"Desconectado de {provider}"}

@router.post("/{provider}/sync")
async def trigger_sync(
    provider: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    """Trigger manual two-way sync for calendar events."""
    user_id = get_user_id(current_user)
    
    result = await db.execute(
        select(UserIntegration).where(
            UserIntegration.user_id == user_id,
            UserIntegration.provider == provider
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integración no encontrada")
        
    # Simulate API call to push/pull events
    # En un entorno real, aquí usaríamos httpx para interactuar con Google/Graph API
    
    integration.last_sync_at = datetime.now(timezone.utc)
    await db.commit()
    
    return {
        "message": "Sincronización completada exitosamente",
        "events_pushed": 3,
        "events_pulled": 1
    }


# --- Webhook Subscriptions Management (User JWT auth) ---

class WebhookSubscriptionIn(BaseModel):
    endpoint_url: str
    event_types: List[str]
    secret: str

class WebhookSubscriptionOut(BaseModel):
    id: str
    tenant_id: str
    event_types: List[str]
    endpoint_url: str
    is_active: bool
    created_at: datetime

@router.post("/webhooks", response_model=WebhookSubscriptionOut)
async def create_webhook_subscription(
    payload: WebhookSubscriptionIn,
    current_user: dict = Depends(get_current_user)
):
    """Register a new webhook subscription for the tenant."""
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id") or current_user.get("tenant_id", "default")
    
    from app.services.webhook_engine import get_webhook_engine, WebhookSubscription
    engine = get_webhook_engine()
    
    sub = WebhookSubscription(
        id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        event_types=payload.event_types,
        endpoint_url=payload.endpoint_url,
        secret=payload.secret,
        is_active=True
    )
    engine.register_subscription(sub)
    
    return WebhookSubscriptionOut(
        id=sub.id,
        tenant_id=sub.tenant_id,
        event_types=sub.event_types,
        endpoint_url=sub.endpoint_url,
        is_active=sub.is_active,
        created_at=sub.created_at
    )

@router.get("/webhooks", response_model=List[WebhookSubscriptionOut])
async def list_webhook_subscriptions(
    current_user: dict = Depends(get_current_user)
):
    """List all webhook subscriptions for the tenant."""
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id") or current_user.get("tenant_id", "default")
    
    from app.services.webhook_engine import get_webhook_engine
    engine = get_webhook_engine()
    
    subs = engine.get_subscriptions(tenant_id)
    return [
        WebhookSubscriptionOut(
            id=sub.id,
            tenant_id=sub.tenant_id,
            event_types=sub.event_types,
            endpoint_url=sub.endpoint_url,
            is_active=sub.is_active,
            created_at=sub.created_at
        )
        for sub in subs
    ]

@router.delete("/webhooks/{sub_id}")
async def delete_webhook_subscription(
    sub_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a webhook subscription."""
    from app.services.webhook_engine import get_webhook_engine
    engine = get_webhook_engine()
    engine.remove_subscription(sub_id)
    return {"message": "Webhook subscription deleted successfully"}


# --- Zapier/Make REST Triggers & Actions (API Key auth) ---

@router.get("/zapier/triggers/employee-hired")
async def zapier_trigger_employee_hired(
    limit: int = 10,
    db: AsyncSession = Depends(get_tenant_db_from_api_key)
):
    """Retrieve recently hired candidates (trigger for employee hired event)."""
    from app.models.hire import Candidate
    result = await db.execute(
        select(Candidate).where(Candidate.stage == "hired").order_by(Candidate.updated_at.desc()).limit(limit)
    )
    candidates = result.scalars().all()
    return [
        {
            "id": c.id,
            "first_name": c.first_name,
            "last_name": c.last_name,
            "email": c.email,
            "stage": c.stage,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None
        }
        for c in candidates
    ]

@router.get("/zapier/triggers/payroll-finalized")
async def zapier_trigger_payroll_finalized(
    limit: int = 10,
    db: AsyncSession = Depends(get_tenant_db_from_api_key)
):
    """Retrieve paid/finalized payroll cycles."""
    from app.models.pay import PayrollCycle
    result = await db.execute(
        select(PayrollCycle).where(PayrollCycle.status == "paid").order_by(PayrollCycle.created_at.desc()).limit(limit)
    )
    cycles = result.scalars().all()
    return [
        {
            "id": c.id,
            "period_name": c.period_name,
            "status": c.status,
            "total_gross": c.total_gross,
            "total_net": c.total_net,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in cycles
    ]

class HireCandidatePayload(BaseModel):
    candidate_id: str
    salary: float | None = None
    start_date: str | None = None

@router.post("/zapier/actions/hire-candidate")
async def zapier_action_hire_candidate(
    payload: HireCandidatePayload,
    db: AsyncSession = Depends(get_tenant_db_from_api_key)
):
    """Mark a candidate as hired and dispatch employee.hired webhook event."""
    from app.models.hire import Candidate
    result = await db.execute(select(Candidate).where(Candidate.id == payload.candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    candidate.stage = "hired"
    candidate.updated_at = datetime.now(timezone.utc)
    await db.commit()
    
    # Dispatch webhook event
    from app.services.webhook_engine import get_webhook_engine
    bind = db.get_bind()
    schema_name = "default"
    if hasattr(bind, "_execution_options"):
        schema_map = bind._execution_options.get("schema_translate_map", {})
        schema_name = schema_map.get(None, "default")
    tenant_id = schema_name.replace("tenant_", "")
    
    event_payload = {
        "candidate_id": candidate.id,
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "email": candidate.email,
        "stage": candidate.stage,
        "salary": payload.salary,
        "start_date": payload.start_date,
        "hired_at": datetime.now(timezone.utc).isoformat()
    }
    
    engine = get_webhook_engine()
    await engine.dispatch_event("employee.hired", event_payload, tenant_id)
    
    return {
        "status": "success",
        "message": f"Candidate {candidate.first_name} {candidate.last_name} hired successfully",
        "data": event_payload
    }

class RunAgentPayload(BaseModel):
    agent_id: str
    input_payload: Dict[str, Any]

@router.post("/zapier/actions/run-agent")
async def zapier_action_run_agent(
    payload: RunAgentPayload,
    db: AsyncSession = Depends(get_tenant_db_from_api_key)
):
    """Execute an AI agent run on behalf of an external integration."""
    from app.services.agent_executor import execute_agent_run
    try:
        result = await execute_agent_run(
            db=db,
            agent_id=payload.agent_id,
            input_payload=payload.input_payload,
            trigger_source="webhook"
        )
        return {
            "status": "success",
            "run_id": result.get("run_id"),
            "reply": result.get("reply"),
            "cost_usd": result.get("cost_usd"),
            "latency_ms": result.get("latency_ms")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")

# --- Jira Integration (Settings & Webhook) ---

class JiraConfigIn(BaseModel):
    jira_url: str
    jira_email: str
    jira_api_token: str
    jira_project_key: str

@router.post("/jira/config")
async def configure_jira(
    payload: JiraConfigIn,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["sys_admin", "hr_admin"]))
):
    """Save Jira configuration for the tenant (mock implementation)."""
    # In reality, store this in TenantMeta or similar.
    return {"message": "Jira configuration saved successfully."}

@router.post("/jira/webhook")
async def jira_webhook(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_tenant_db_from_api_key)
):
    """Receive issue updates from Jira to sync back to ITTicket."""
    from sqlalchemy import select
    from app.models.it import ITTicket
    
    issue = payload.get("issue", {})
    issue_key = issue.get("key")
    if not issue_key:
        return {"status": "ignored"}
        
    # Search for ticket that has this jira_key in its meta
    # Because ticket_meta is JSON, doing a simple fetch and filter or json-based query depending on dialect
    # For now, we simulate matching the ticket
    res = await db.execute(select(ITTicket))
    tickets = res.scalars().all()
    matched_ticket = None
    for t in tickets:
        if isinstance(t.ticket_meta, dict) and t.ticket_meta.get("jira_key") == issue_key:
            matched_ticket = t
            break
            
    if matched_ticket:
        # Update status based on Jira status
        status_name = issue.get("fields", {}).get("status", {}).get("name", "").lower()
        if status_name in ["done", "resolved", "closed"]:
            matched_ticket.status = "resolved"
        elif status_name in ["in progress"]:
            matched_ticket.status = "in_progress"
            
        await db.commit()
        return {"status": "success", "ticket_id": matched_ticket.id}
        
    return {"status": "not_found"}

