from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timezone

from app.api.dependencies import get_tenant_db_from_api_key

router = APIRouter()

# --- Power Automate Triggers (Polling) ---

@router.get("/triggers/new-employee")
async def power_automate_trigger_new_employee(
    limit: int = 10,
    db: AsyncSession = Depends(get_tenant_db_from_api_key)
):
    """Recupera los empleados añadidos recientemente para el polling de Power Automate."""
    # Los empleados se modelan como User en app.models.user (no existe un modelo Employee separado)
    from app.models.user import User
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).limit(limit)
    )
    employees = result.scalars().all()
    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "department": u.department,
            "role": u.role,
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in employees
    ]

@router.get("/triggers/new-ticket")
async def power_automate_trigger_new_ticket(
    limit: int = 10,
    db: AsyncSession = Depends(get_tenant_db_from_api_key)
):
    """Retrieve recently created IT tickets for Power Automate polling."""
    from app.models.it import ITTicket
    result = await db.execute(
        select(ITTicket).order_by(ITTicket.created_at.desc()).limit(limit)
    )
    tickets = result.scalars().all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "status": t.status,
            "priority": t.priority,
            "created_at": t.created_at.isoformat() if t.created_at else None
        }
        for t in tickets
    ]

@router.get("/triggers/leave-requests")
async def power_automate_trigger_leave_requests(
    limit: int = 10,
    db: AsyncSession = Depends(get_tenant_db_from_api_key)
):
    """Recupera las solicitudes de ausencia pendientes para el polling de Power Automate."""
    # Las ausencias/vacaciones viven en VacationRequest (app.models.calendar)
    from app.models.calendar import VacationRequest
    result = await db.execute(
        select(VacationRequest).where(VacationRequest.status == "pending").order_by(VacationRequest.created_at.desc()).limit(limit)
    )
    requests = result.scalars().all()
    return [
        {
            "id": r.id,
            "employee_id": r.user_id,
            "type": r.absence_type,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in requests
    ]


# --- Power Automate Actions (Push) ---

class RunAgentPayload(BaseModel):
    agent_id: str
    input_payload: Dict[str, Any]

@router.post("/actions/run-agent")
async def power_automate_action_run_agent(
    payload: RunAgentPayload,
    db: AsyncSession = Depends(get_tenant_db_from_api_key)
):
    """Execute an AI agent run from Power Automate."""
    from app.services.agent_executor import execute_agent_run
    try:
        result = await execute_agent_run(
            db=db,
            agent_id=payload.agent_id,
            input_payload=payload.input_payload,
            trigger_source="power_automate"
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

class CreateTicketPayload(BaseModel):
    title: str
    description: str
    priority: str = "medium"

@router.post("/actions/create-ticket")
async def power_automate_action_create_ticket(
    payload: CreateTicketPayload,
    db: AsyncSession = Depends(get_tenant_db_from_api_key)
):
    """Create a new IT Ticket from Power Automate."""
    from app.models.it import ITTicket
    import uuid
    
    new_ticket = ITTicket(
        id=uuid.uuid4().hex,
        title=payload.title,
        description=payload.description,
        status="open",
        priority=payload.priority,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(new_ticket)
    await db.commit()
    
    return {
        "status": "success",
        "message": "Ticket created successfully",
        "ticket_id": new_ticket.id
    }

class SendNotificationPayload(BaseModel):
    user_id: str
    title: str
    message: str
    type: str = "info"

@router.post("/actions/send-notification")
async def power_automate_action_send_notification(
    payload: SendNotificationPayload,
    db: AsyncSession = Depends(get_tenant_db_from_api_key)
):
    """Send an internal notification to an employee/user from Power Automate."""
    from app.models.notification import Notification
    import uuid
    
    new_notif = Notification(
        id=uuid.uuid4().hex,
        user_id=payload.user_id,
        title=payload.title,
        message=payload.message,
        type=payload.type,
        is_read=False,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_notif)
    await db.commit()
    
    return {
        "status": "success",
        "message": "Notification sent successfully",
        "notification_id": new_notif.id
    }
