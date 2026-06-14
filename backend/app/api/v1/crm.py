from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import json

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.dependencies import get_tenant_db, require_roles
from app.models.sales import Client, Lead
import uuid

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

# --- Schemas ---
class ClientCreate(BaseModel):
    company_name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    primary_contact_phone: Optional[str] = None

class ClientResponse(ClientCreate):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class LeadCreate(BaseModel):
    title: str
    contact_name: Optional[str] = None
    company_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    estimated_value: Optional[float] = 0.0
    probability: Optional[int] = 10
    stage: Optional[str] = "inbound"
    client_id: Optional[str] = None

class LeadResponse(LeadCreate):
    id: str
    expected_close_date: Optional[datetime] = None
    created_at: datetime
    score: Optional[float] = 0.0
    score_breakdown: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class StageUpdate(BaseModel):
    stage: str

class PipelineConfig(BaseModel):
    stages: List[str]

# --- Default Pipeline Stages ---
DEFAULT_STAGES = ["inbound", "discovery", "proposal", "negotiation", "won", "lost"]

# --- Endpoints ---

@router.get("/stages", response_model=List[str])
async def get_pipeline_stages(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Retorna las etapas activas del pipeline de ventas.
    """
    return DEFAULT_STAGES

@router.get("/leads", response_model=List[LeadResponse])
async def get_crm_leads(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Lista todos los leads (negocios/deals) del CRM.
    """
    result = await db.execute(select(Lead).order_by(Lead.created_at.desc()))
    return result.scalars().all()

@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_crm_lead(
    data: LeadCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Crea un nuevo lead de ventas en el CRM.
    """
    db_lead = Lead(
        id=str(uuid.uuid4()),
        title=data.title,
        contact_name=data.contact_name,
        company_name=data.company_name,
        email=data.email,
        phone=data.phone,
        estimated_value=data.estimated_value,
        probability=data.probability,
        stage=data.stage,
        client_id=data.client_id
    )
    db.add(db_lead)
    await db.commit()
    await db.refresh(db_lead)
    return db_lead

@router.patch("/leads/{lead_id}/stage")
@limiter.limit("30/minute")
async def update_crm_lead_stage(
    lead_id: str,
    payload: StageUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Actualiza la etapa de un lead específico (ideal para mover tarjetas en el tablero Kanban).
    """
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
        
    lead.stage = payload.stage
    await db.commit()
    return {"message": "Etapa del lead actualizada exitosamente"}

@router.get("/contacts")
async def get_crm_contacts(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Lista todos los contactos (clientes/companies) del CRM.
    Remapea campos de sales_clients a formato esperado por el frontend.
    """
    result = await db.execute(select(Client).order_by(Client.created_at.desc()))
    clients = result.scalars().all()
    return {
        "contacts": [
            {
                "id": c.id,
                "orgId": "default",
                "firstName": c.primary_contact_name or "",
                "lastName": "",
                "company": c.company_name or "",
                "title": c.industry or "",
                "email": c.primary_contact_email or None,
                "phone": c.primary_contact_phone or None,
                "source": "manual",
                "tags": "[]",
                "customFields": "{}",
                "score": 50,
                "lastActivity": c.created_at.isoformat() if c.created_at else None,
                "createdAt": c.created_at.isoformat() if c.created_at else None,
            }
            for c in clients
        ]
    }

@router.post("/contacts", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_crm_contact(
    data: ClientCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Crea un nuevo contacto de cliente en el CRM.
    """
    db_client = Client(
        id=str(uuid.uuid4()),
        company_name=data.company_name,
        industry=data.industry,
        website=data.website,
        primary_contact_name=data.primary_contact_name,
        primary_contact_email=data.primary_contact_email,
        primary_contact_phone=data.primary_contact_phone
    )
    db.add(db_client)
    await db.commit()
    await db.refresh(db_client)
    return db_client

@router.get("/contacts/{contact_id}")
async def get_crm_contact_details(
    contact_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Obtiene los detalles de un contacto específico del CRM, incluyendo sus negocios y actividades simuladas.
    """
    result = await db.execute(select(Client).where(Client.id == contact_id))
    client = result.scalars().first()
    if not client:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
        
    leads_res = await db.execute(select(Lead).where(Lead.client_id == contact_id))
    leads = leads_res.scalars().all()
    
    activities = [
        {
            "id": "act_1",
            "title": "Contacto creado",
            "type": "system",
            "content": "El contacto fue ingresado en el sistema CRM.",
            "createdAt": client.created_at.isoformat() if client.created_at else datetime.now().isoformat()
        },
        {
            "id": "act_2",
            "title": "Llamada de seguimiento",
            "type": "call",
            "content": "Conversación introductoria. El cliente muestra interés en servicios corporativos.",
            "createdAt": datetime.now().isoformat()
        }
    ]
    
    return {
        "contact": {
            "id": client.id,
            "firstName": client.primary_contact_name,
            "lastName": "",
            "company": client.company_name,
            "title": client.industry,
            "email": client.primary_contact_email,
            "phone": client.primary_contact_phone,
            "lastActivity": datetime.now().isoformat(),
            "deals": [
                {
                    "id": l.id,
                    "title": l.title,
                    "currency": "$",
                    "value": l.estimated_value,
                    "stage": l.stage,
                    "probability": l.probability
                } for l in leads
            ],
            "activities": activities
        }
    }

@router.post("/contacts/{contact_id}")
@limiter.limit("30/minute")
async def create_contact_activity(
    contact_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Simula el registro de una actividad para el contacto.
    """
    result = await db.execute(select(Client).where(Client.id == contact_id))
    client = result.scalars().first()
    if not client:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return {"status": "success", "message": "Actividad registrada exitosamente"}

@router.delete("/contacts/{contact_id}")
@limiter.limit("30/minute")
async def delete_crm_contact(
    contact_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Elimina un contacto del CRM.
    """
    result = await db.execute(select(Client).where(Client.id == contact_id))
    client = result.scalars().first()
    if not client:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
        
    await db.delete(client)
    await db.commit()
    return {"status": "success", "message": "Contacto eliminado exitosamente"}

@router.get("/leads/{lead_id}")
async def get_crm_lead_details(
    lead_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Obtiene los detalles de un lead específico, incluyendo su contacto asociado y actividades simuladas.
    """
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
        
    contact = None
    if lead.client_id:
        client_res = await db.execute(select(Client).where(Client.id == lead.client_id))
        client = client_res.scalars().first()
        if client:
            contact = {
                "id": client.id,
                "firstName": client.primary_contact_name,
                "lastName": "",
                "company": client.company_name,
                "email": client.primary_contact_email,
                "phone": client.primary_contact_phone
            }
            
    activities = [
        {
            "id": "act_1",
            "title": "Oportunidad creada",
            "type": "system",
            "content": f"Se creó el negocio '{lead.title}' en la etapa '{lead.stage}'.",
            "createdAt": lead.created_at.isoformat() if lead.created_at else datetime.now().isoformat()
        }
    ]
    
    return {
        "deal": {
            "id": lead.id,
            "title": lead.title,
            "currency": "$",
            "value": lead.estimated_value,
            "stage": lead.stage,
            "probability": lead.probability,
            "contactId": lead.client_id,
            "contact": contact,
            "activities": activities
        }
    }

@router.patch("/leads/{lead_id}")
@limiter.limit("30/minute")
async def update_crm_lead(
    lead_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Actualiza cualquier campo de un lead.
    """
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
        
    if "title" in payload:
        lead.title = payload["title"]
    if "estimated_value" in payload:
        lead.estimated_value = float(payload["estimated_value"] or 0.0)
    if "probability" in payload:
        lead.probability = int(payload["probability"] or 10)
    if "stage" in payload:
        lead.stage = payload["stage"]
        
    await db.commit()
    return {"status": "success", "message": "Negocio actualizado exitosamente"}

@router.post("/leads/{lead_id}")
@limiter.limit("30/minute")
async def create_lead_activity(
    lead_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Simula el registro de una actividad para el lead.
    """
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    return {"status": "success", "message": "Actividad registrada exitosamente"}

@router.delete("/leads/{lead_id}")
@limiter.limit("30/minute")
async def delete_crm_lead(
    lead_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Elimina un negocio (lead) del CRM.
    """
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
        
    await db.delete(lead)
    await db.commit()
    return {"status": "success", "message": "Negocio eliminado exitosamente"}

# --- AI-F9: Intelligent Lead Scoring & Next Best Action ---

class EmailTemplateRequest(BaseModel):
    email_type: str

class ConversationAnalysisRequest(BaseModel):
    transcript: str
    deal_context: str = ""

@router.post("/leads/{lead_id}/score")
@limiter.limit("30/minute")
async def ai_score_lead(
    lead_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.services.lead_scorer import score_lead as do_score
    result = await do_score(lead_id, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.post("/leads/{lead_id}/next-action")
@limiter.limit("30/minute")
async def ai_next_action(
    lead_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.services.lead_scorer import suggest_next_action as do_action
    result = await do_action(lead_id, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.get("/pipeline/score-board")
async def ai_pipeline_scoreboard(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    try:
        from app.core.redis import get_redis
        r = await get_redis()
        cached = await r.get("crm:pipeline:scoreboard")
        if cached:
            return json.loads(cached)
    except Exception:
        pass
    from app.services.lead_scorer import batch_score_pipeline as do_batch
    return await do_batch(db)

@router.post("/leads/{lead_id}/email-template")
@limiter.limit("30/minute")
async def ai_email_template(
    lead_id: str,
    payload: EmailTemplateRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.services.lead_scorer import generate_email_template as do_email
    result = await do_email(lead_id, payload.email_type, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/leads/{lead_id}/predict-probability")
@limiter.limit("30/minute")
async def ai_predict_probability(
    lead_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.services.lead_scorer import predict_deal_probability as do_predict
    result = await do_predict(lead_id, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.post("/conversation/analyze")
@limiter.limit("30/minute")
async def ai_analyze_conversation(
    payload: ConversationAnalysisRequest,
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.services.lead_scorer import analyze_sales_conversation as do_analyze
    return await do_analyze(payload.transcript, payload.deal_context)
