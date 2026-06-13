from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func
from typing import List, Optional
from datetime import datetime, date, timedelta, timezone
from app.api.dependencies import get_tenant_db, require_roles, check_module_enabled
from app.models.it import ITAsset, ITTicket, SaaSLicense, ITRequisition, ITKnowledgeArticle
from app.models.user import User
from app.schemas.it import (
    ITAssetCreate, ITAssetResponse, ITAssetUpdate,
    ITTicketCreate, ITTicketResponse, ITTicketUpdate,
    SaaSLicenseCreate, SaaSLicenseResponse, SaaSLicenseUpdate,
    ITRequisitionCreate, ITRequisitionResponse, ITRequisitionUpdate,
    ITKnowledgeArticleResponse, KBListResponse
)
import uuid

router = APIRouter(dependencies=[Depends(check_module_enabled("it"))])



# ==========================================
# IT ASSETS ENDPOINTS
# ==========================================
def _add_depreciation(a: ITAsset):
    from datetime import date
    if a.cost and a.purchase_date:
        cost = float(a.cost)
        cat = (a.category or "laptop").lower()
        if cat == "laptop":
            useful_life_years = 3.0
        elif cat == "mobile":
            useful_life_years = 2.0
        else:
            useful_life_years = 4.0
            
        useful_life_days = useful_life_years * 365.25
        # Convert date to date if it's datetime
        p_date = a.purchase_date.date() if isinstance(a.purchase_date, datetime) else a.purchase_date
        days_owned = (date.today() - p_date).days
        
        if days_owned <= 0:
            accum = 0.0
        elif days_owned >= useful_life_days:
            accum = cost
        else:
            accum = (cost / useful_life_days) * days_owned
            
        a.accumulated_depreciation = round(accum, 2)
        a.net_book_value = round(max(0.0, cost - accum), 2)
    else:
        a.accumulated_depreciation = 0.0
        a.net_book_value = 0.0
    return a


@router.get("/assets", response_model=List[ITAssetResponse])
async def list_assets(
    category: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Listar todos los activos de hardware (inventario)."""
    query = select(ITAsset)
    if category:
        query = query.where(ITAsset.category == category)
    if status:
        query = query.where(ITAsset.status == status)
    
    result = await db.execute(query.order_by(ITAsset.created_at.desc()))
    assets = result.scalars().all()
    for a in assets:
        _add_depreciation(a)
    return assets


@router.post("/assets", response_model=ITAssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset_in: ITAssetCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """Crear/añadir un nuevo activo de hardware."""
    asset = ITAsset(
        id=uuid.uuid4().hex,
        **asset_in.model_dump()
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return _add_depreciation(asset)


@router.put("/assets/{asset_id}", response_model=ITAssetResponse)
async def update_asset(
    asset_id: str,
    asset_in: ITAssetUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """Actualizar detalles de un activo de hardware."""
    result = await db.execute(select(ITAsset).where(ITAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Activo de IT no encontrado")

    for field, value in asset_in.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)

    await db.commit()
    await db.refresh(asset)
    return _add_depreciation(asset)


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """Eliminar un activo de hardware."""
    result = await db.execute(select(ITAsset).where(ITAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Activo de IT no encontrado")

    await db.delete(asset)
    await db.commit()
    return None


# ==========================================
# IT TICKETS ENDPOINTS
# ==========================================
@router.get("/tickets", response_model=List[ITTicketResponse])
async def list_tickets(
    status: Optional[str] = None,
    requester_id: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Listar tickets de soporte técnico. Los empleados comunes solo ven sus propios tickets."""
    query = select(ITTicket)
    
    # Filtro de rol
    if user_payload.get("role") == "employee":
        query = query.where(ITTicket.requester_id == user_payload.get("user_id"))
    elif requester_id:
        query = query.where(ITTicket.requester_id == requester_id)
        
    if status:
        query = query.where(ITTicket.status == status)
        
    result = await db.execute(query.order_by(ITTicket.created_at.desc()))
    return result.scalars().all()


@router.post("/tickets", response_model=ITTicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_in: ITTicketCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    if user_payload.get("role") == "employee" and ticket_in.requester_id != user_payload.get("user_id"):
        raise HTTPException(status_code=403, detail="No puedes crear tickets a nombre de otro usuario")

    ticket = ITTicket(
        id=uuid.uuid4().hex,
        **ticket_in.model_dump()
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    if ticket.assignee_id:
        try:
            from app.services.notification_utils import create_and_push_notification
            await create_and_push_notification(
                db,
                user_id=ticket.assignee_id,
                title="New Ticket Assigned",
                message=f"Ticket '{ticket.title}' has been assigned to you",
                type_="task",
                link="/dashboard/it?tab=tickets",
            )
            await db.commit()
        except Exception:
            pass

    background_tasks.add_task(_run_kb_suggestions, ticket.id, db)
    background_tasks.add_task(_run_kb_auto_tag, ticket.id, db)

    from app.services.jira_client import push_ticket_to_jira
    background_tasks.add_task(push_ticket_to_jira, ticket.id, db)

    return ticket


async def _run_kb_suggestions(ticket_id: str, db: AsyncSession):
    try:
        from app.services.it_knowledge_base import suggest_solutions
        result = await suggest_solutions(ticket_id, db)
        logger = __import__("logging").getLogger(__name__)
        ticket_result = await db.execute(select(ITTicket).where(ITTicket.id == ticket_id))
        ticket = ticket_result.scalar_one_or_none()
        if ticket:
            meta = ticket.ticket_meta or {}
            meta["kb_suggestions"] = result
            ticket.ticket_meta = meta
            await db.commit()
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.error(f"Background task suggest_solutions failed: {e}")


async def _run_kb_auto_tag(ticket_id: str, db: AsyncSession):
    try:
        from app.services.it_knowledge_base import auto_tag_ticket
        await auto_tag_ticket(ticket_id, db)
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.error(f"Background task auto_tag_ticket failed: {e}")


@router.put("/tickets/{ticket_id}", response_model=ITTicketResponse)
async def update_ticket(
    ticket_id: str,
    ticket_in: ITTicketUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    result = await db.execute(select(ITTicket).where(ITTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    if user_payload.get("role") == "employee":
        if ticket.requester_id != user_payload.get("user_id"):
            raise HTTPException(status_code=403, detail="No tienes permiso para modificar este ticket")
        if ticket_in.status and ticket_in.status not in ["closed", "resolved"]:
            raise HTTPException(status_code=403, detail="Operación no permitida")

    previous_status = ticket.status
    previous_assignee_id = ticket.assignee_id
    for field, value in ticket_in.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)

    if ticket_in.status and ticket_in.status in ["resolved", "closed"] and previous_status not in ["resolved", "closed"]:
        ticket.resolved_at = datetime.now(ticket.created_at.tzinfo) if ticket.created_at and ticket.created_at.tzinfo else datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(ticket)

    if ticket.assignee_id and ticket.assignee_id != previous_assignee_id:
        try:
            from app.services.notification_utils import create_and_push_notification
            await create_and_push_notification(
                db,
                user_id=ticket.assignee_id,
                title="Ticket Assigned to You",
                message=f"Ticket '{ticket.title}' has been assigned to you",
                type_="task",
                link="/dashboard/it?tab=tickets",
            )
            await db.commit()
        except Exception:
            pass

    await _check_sla_breach(ticket, db)

    if ticket.status in ["resolved", "closed"] and previous_status not in ["resolved", "closed"]:
        background_tasks.add_task(_run_kb_generate_article, ticket.id, db)

    return ticket


async def _check_sla_breach(ticket: ITTicket, db: AsyncSession):
    now = datetime.now(timezone.utc)
    hours_open = (now - ticket.created_at).total_seconds() / 3600
    if hours_open > 24 and ticket.status in ("open", "in_progress"):
        meta = ticket.ticket_meta or {}
        if not meta.get("sla_notified"):
            meta["sla_notified"] = True
            ticket.ticket_meta = meta
            try:
                from app.services.broadcast import broadcast_notification
                await broadcast_notification(
                    db,
                    title=f"SLA Breach: {ticket.title}",
                    message=f"Ticket '{ticket.title}' has been open for {hours_open:.1f} hours (SLA: 24h)",
                    type_="system",
                    role="hr_admin",
                    link="/dashboard/it?tab=tickets",
                )
            except Exception:
                pass


async def _run_kb_generate_article(ticket_id: str, db: AsyncSession):
    try:
        from app.services.it_knowledge_base import generate_kb_article, index_resolved_tickets
        await generate_kb_article(ticket_id, db)
        await index_resolved_tickets(db)
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.error(f"Background task generate_kb_article failed: {e}")


# ==========================================
# SAAS LICENSES ENDPOINTS
# ==========================================
@router.get("/licenses", response_model=List[SaaSLicenseResponse])
async def list_licenses(
    assigned_to_id: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """Listar licencias SaaS del tenant."""
    query = select(SaaSLicense)
    if assigned_to_id:
        query = query.where(SaaSLicense.assigned_to_id == assigned_to_id)
        
    result = await db.execute(query.order_by(SaaSLicense.created_at.desc()))
    return result.scalars().all()


@router.post("/licenses", response_model=SaaSLicenseResponse, status_code=status.HTTP_201_CREATED)
async def create_license(
    lic_in: SaaSLicenseCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """Crear/provisionar una nueva licencia SaaS."""
    lic = SaaSLicense(
        id=uuid.uuid4().hex,
        **lic_in.model_dump()
    )
    db.add(lic)
    await db.commit()
    await db.refresh(lic)
    return lic


@router.put("/licenses/{license_id}", response_model=SaaSLicenseResponse)
async def update_license(
    license_id: str,
    lic_in: SaaSLicenseUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """Actualizar una licencia SaaS."""
    result = await db.execute(select(SaaSLicense).where(SaaSLicense.id == license_id))
    lic = result.scalar_one_or_none()
    if not lic:
        raise HTTPException(status_code=404, detail="Licencia SaaS no encontrada")

    for field, value in lic_in.model_dump(exclude_unset=True).items():
        setattr(lic, field, value)

    await db.commit()
    await db.refresh(lic)
    return lic


@router.delete("/licenses/{license_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_license(
    license_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """Eliminar una licencia SaaS."""
    result = await db.execute(select(SaaSLicense).where(SaaSLicense.id == license_id))
    lic = result.scalar_one_or_none()
    if not lic:
        raise HTTPException(status_code=404, detail="Licencia SaaS no encontrada")

    await db.delete(lic)
    await db.commit()
    return None


# ==========================================
# BI & ANALYTICS ODATA STREAM
# ==========================================
@router.get("/analytics/odata")
async def get_bi_stream(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """
    Feed de datos de IT y RRHH optimizado para Power BI y Tableau.
    Retorna un JSON estructurado con esquemas relacionales planos listos para ingesta directa.
    """
    # Ingesta plana de usuarios
    users_res = await db.execute(select(User))
    users = users_res.scalars().all()
    
    # Ingesta plana de activos
    assets_res = await db.execute(select(ITAsset))
    assets = assets_res.scalars().all()
    
    # Ingesta plana de licencias
    licenses_res = await db.execute(select(SaaSLicense))
    licenses = licenses_res.scalars().all()
    
    # Ingesta plana de tickets
    tickets_res = await db.execute(select(ITTicket))
    tickets = tickets_res.scalars().all()

    return {
        "value": {
            "users": [
                {
                    "id": u.id,
                    "email": u.email,
                    "full_name": u.full_name,
                    "department": u.department,
                    "role": u.role,
                    "is_active": u.is_active,
                    "created_at": u.created_at.isoformat() if u.created_at else None
                } for u in users
            ],
            "assets": [
                {
                    "id": a.id,
                    "name": a.name,
                    "serial_number": a.serial_number,
                    "category": a.category,
                    "status": a.status,
                    "assigned_to_id": a.assigned_to_id,
                    "purchase_date": a.purchase_date.isoformat() if a.purchase_date else None,
                    "cost": float(a.cost) if a.cost else 0.0
                } for a in assets
            ],
            "licenses": [
                {
                    "id": l.id,
                    "software_name": l.software_name,
                    "seat_cost": float(l.seat_cost),
                    "assigned_to_id": l.assigned_to_id,
                    "status": l.status,
                    "renewal_date": l.renewal_date.isoformat() if l.renewal_date else None
                } for l in licenses
            ],
            "tickets": [
                {
                    "id": t.id,
                    "title": t.title,
                    "category": t.category,
                    "priority": t.priority,
                    "status": t.status,
                    "requester_id": t.requester_id,
                    "assignee_id": t.assignee_id,
                    "created_at": t.created_at.isoformat() if t.created_at else None
                } for t in tickets
            ]
        }
    }


# ==========================================
# IT REQUISITIONS ENDPOINTS (SAP MM / ITSM)
# ==========================================
@router.get("/requisitions", response_model=List[ITRequisitionResponse])
async def list_requisitions(
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Listar solicitudes de aprovisionamiento de IT."""
    query = select(ITRequisition)
    user_roles = user_payload.get("roles", []) or user_payload.get("https://successcore.com/app_metadata", {}).get("roles", [])
    
    # If not hr_admin, filter only their own requisitions
    if "employee" in user_roles and "hr_admin" not in user_roles:
        sub = user_payload.get("sub", "")
        u_id = sub.split("|")[-1] if "|" in sub else sub
        query = query.where(ITRequisition.user_id == u_id)
        
    result = await db.execute(query.order_by(ITRequisition.created_at.desc()))
    return result.scalars().all()


@router.post("/requisitions", response_model=ITRequisitionResponse, status_code=status.HTTP_201_CREATED)
async def create_requisition(
    req_in: ITRequisitionCreate,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Crear una nueva solicitud de aprovisionamiento."""
    sub = user_payload.get("sub", "")
    u_id = sub.split("|")[-1] if "|" in sub else sub
    
    requisition = ITRequisition(
        id=uuid.uuid4().hex,
        user_id=u_id,
        **req_in.model_dump()
    )
    db.add(requisition)
    await db.commit()
    await db.refresh(requisition)
    return requisition


@router.put("/requisitions/{req_id}/status", response_model=ITRequisitionResponse)
async def update_requisition_status(
    req_id: str,
    req_in: ITRequisitionUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """Aprobar o rechazar una solicitud (Solo HR/IT Admin)."""
    result = await db.execute(select(ITRequisition).where(ITRequisition.id == req_id))
    requisition = result.scalar_one_or_none()
    if not requisition:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    requisition.status = req_in.status
    
    # SAP ITSM / MM integration: if approved, provision the asset or license automatically
    if req_in.status == "approved":
        if requisition.item_type == "hardware":
            # Auto-provision a new ITAsset
            new_asset = ITAsset(
                id=uuid.uuid4().hex,
                name=requisition.item_name,
                serial_number=f"SN-{uuid.uuid4().hex[:8].upper()}",
                category="laptop",
                status="assigned",
                assigned_to_id=requisition.user_id,
                purchase_date=date.today(),
                cost=1200.00
            )
            db.add(new_asset)
        elif requisition.item_type == "software":
            # Auto-provision a new SaaSLicense
            new_license = SaaSLicense(
                id=uuid.uuid4().hex,
                software_name=requisition.item_name,
                seat_cost=15.00,
                assigned_to_id=requisition.user_id,
                status="active",
                renewal_date=date.today() + timedelta(days=365)
            )
            db.add(new_license)

    await db.commit()
    await db.refresh(requisition)
    return requisition


# ==========================================
# IT KNOWLEDGE BASE ENDPOINTS
# ==========================================

@router.post("/kb/index-tickets")
async def kb_index_tickets(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["sys_admin"]))
):
    from app.services.it_knowledge_base import index_resolved_tickets
    result = await index_resolved_tickets(db)
    return result


@router.post("/kb/generate-article/{ticket_id}")
async def kb_generate_article(
    ticket_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.it_knowledge_base import generate_kb_article
    result = await generate_kb_article(ticket_id, db)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Failed to generate article"))
    return result


@router.get("/kb/search")
async def kb_search(
    query: str = Query(..., description="Search query"),
    top_k: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "employee", "sys_admin"]))
):
    from app.services.it_knowledge_base import search_kb_articles
    results = await search_kb_articles(query, db, top_k=top_k)
    return {"status": "success", "query": query, "top_k": top_k, "results": results}


@router.get("/kb/articles", response_model=KBListResponse)
async def kb_list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "employee", "sys_admin"]))
):
    query = select(ITKnowledgeArticle)
    if category:
        query = query.where(ITKnowledgeArticle.category == category)
    result = await db.execute(
        query.order_by(ITKnowledgeArticle.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )

    count_query = select(sa_func.count()).select_from(ITKnowledgeArticle)
    if category:
        count_query = count_query.where(ITKnowledgeArticle.category == category)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    items = result.scalars().all()
    return KBListResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/kb/articles/{article_id}", response_model=ITKnowledgeArticleResponse)
async def kb_get_article(
    article_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "employee", "sys_admin"]))
):
    result = await db.execute(select(ITKnowledgeArticle).where(ITKnowledgeArticle.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="KB article not found")
    article.view_count += 1
    await db.commit()
    await db.refresh(article)
    return article


@router.post("/tickets/{ticket_id}/suggest")
async def ticket_suggest_solutions(
    ticket_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "employee", "sys_admin"]))
):
    from app.services.it_knowledge_base import suggest_solutions
    result = await suggest_solutions(ticket_id, db)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Failed to suggest solutions"))
    return result


@router.post("/tickets/{ticket_id}/auto-tag")
async def ticket_auto_tag(
    ticket_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.it_knowledge_base import auto_tag_ticket
    result = await auto_tag_ticket(ticket_id, db)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Failed to auto-tag"))
    return result


@router.get("/kb/recurring-issues")
async def kb_recurring_issues(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.it_knowledge_base import detect_recurring_issues
    result = await detect_recurring_issues(db)
    return result


@router.get("/kb/preventive-actions")
async def kb_preventive_actions(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.it_knowledge_base import suggest_preventive_actions
    result = await suggest_preventive_actions(category=category, db=db)
    return result


@router.post("/tickets/{ticket_id}/sla-estimate")
async def ticket_sla_estimate(
    ticket_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "employee", "sys_admin"]))
):
    from app.services.it_knowledge_base import suggest_sla_estimate
    result = await suggest_sla_estimate(ticket_id, db)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Failed to estimate SLA"))
    return result


@router.get("/sla/summary")
async def get_sla_summary(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "employee", "sys_admin"]))
):
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    result = await db.execute(select(ITTicket))
    all_tickets = result.scalars().all()

    total = len(all_tickets)
    open_tickets = [t for t in all_tickets if t.status in ("open", "in_progress")]
    resolved = [t for t in all_tickets if t.status == "resolved"]
    breached = [t for t in all_tickets if t.ticket_meta and t.ticket_meta.get("sla_breached")]

    age_buckets = {"<4h": 0, "4-8h": 0, "8-24h": 0, "24-72h": 0, ">72h": 0}
    for t in open_tickets:
        age_hours = (now - t.created_at).total_seconds() / 3600
        if age_hours < 4:
            age_buckets["<4h"] += 1
        elif age_hours < 8:
            age_buckets["4-8h"] += 1
        elif age_hours < 24:
            age_buckets["8-24h"] += 1
        elif age_hours < 72:
            age_buckets["24-72h"] += 1
        else:
            age_buckets[">72h"] += 1

    avg_resolution_hours = 0.0
    if resolved:
        resolved_with_updates = [t for t in resolved if t.updated_at]
        if resolved_with_updates:
            total_hours = sum(
                ((t.updated_at - t.created_at).total_seconds() / 3600)
                for t in resolved_with_updates
            )
            avg_resolution_hours = round(total_hours / len(resolved), 1)

    priority_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for t in open_tickets:
        p = t.priority.lower() if t.priority else "medium"
        if p in priority_counts:
            priority_counts[p] += 1

    response_data = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        opened_count = sum(
            1 for t in all_tickets
            if t.created_at and day_start <= t.created_at < day_end
        )
        resolved_count = sum(
            1 for t in all_tickets
            if t.resolved_at and day_start <= t.resolved_at < day_end
        )
        response_data.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "opened": opened_count,
            "resolved": resolved_count,
        })

    return {
        "total_open": len(open_tickets),
        "total_resolved": len(resolved),
        "sla_breached": len(breached),
        "breach_pct": round(len(breached) / max(len(open_tickets), 1) * 100, 1),
        "avg_resolution_hours": avg_resolution_hours,
        "age_distribution": age_buckets,
        "priority_distribution": priority_counts,
        "response_data": response_data,
    }


@router.get("/assets/summary", response_model=dict)
async def get_asset_summary(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "employee", "sys_admin"]))
):
    from app.services.it_asset_service import get_asset_summary, get_warranty_alerts
    summary = await get_asset_summary(db)
    alerts = await get_warranty_alerts(db)
    summary["warranty_alerts"] = alerts
    return summary
