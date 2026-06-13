from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.api.dependencies import get_tenant_db, require_roles, get_current_user
from app.models.agent import AgentTriggerConfig
from app.services.event_trigger_service import get_trigger_queue, approve_trigger, reject_trigger
import uuid

router = APIRouter()


class TriggerCreate(BaseModel):
    agent_id: str
    event_type: str
    filter_condition: dict = None
    input_template: str = None
    auto_approve: bool = False
    is_active: bool = True
    max_executions_per_hour: int = 10


class TriggerUpdate(BaseModel):
    event_type: str = None
    filter_condition: dict = None
    input_template: str = None
    auto_approve: bool = None
    is_active: bool = None
    max_executions_per_hour: int = None


@router.get("/")
async def list_triggers(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(AgentTriggerConfig).order_by(AgentTriggerConfig.created_at.desc())
    )
    triggers = result.scalars().all()
    return [
        {
            "id": t.id,
            "agent_id": t.agent_id,
            "event_type": t.event_type,
            "filter_condition": t.filter_condition,
            "input_template": t.input_template,
            "auto_approve": t.auto_approve,
            "is_active": t.is_active,
            "max_executions_per_hour": t.max_executions_per_hour,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in triggers
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_trigger(
    body: TriggerCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(get_current_user),
):
    trigger = AgentTriggerConfig(
        id=uuid.uuid4().hex,
        agent_id=body.agent_id,
        event_type=body.event_type,
        filter_condition=body.filter_condition,
        input_template=body.input_template,
        auto_approve=body.auto_approve,
        is_active=body.is_active,
        max_executions_per_hour=body.max_executions_per_hour,
    )
    db.add(trigger)
    await db.commit()
    await db.refresh(trigger)
    return {"id": trigger.id, "agent_id": trigger.agent_id, "event_type": trigger.event_type, "is_active": trigger.is_active}


@router.put("/{trigger_id}")
async def update_trigger(
    trigger_id: str,
    body: TriggerUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(AgentTriggerConfig).where(AgentTriggerConfig.id == trigger_id)
    )
    trigger = result.scalar_one_or_none()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    if body.event_type is not None:
        trigger.event_type = body.event_type
    if body.filter_condition is not None:
        trigger.filter_condition = body.filter_condition
    if body.input_template is not None:
        trigger.input_template = body.input_template
    if body.auto_approve is not None:
        trigger.auto_approve = body.auto_approve
    if body.is_active is not None:
        trigger.is_active = body.is_active
    if body.max_executions_per_hour is not None:
        trigger.max_executions_per_hour = body.max_executions_per_hour

    await db.commit()
    await db.refresh(trigger)
    return {"id": trigger.id, "event_type": trigger.event_type, "is_active": trigger.is_active}


@router.delete("/{trigger_id}")
async def delete_trigger(
    trigger_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(AgentTriggerConfig).where(AgentTriggerConfig.id == trigger_id)
    )
    trigger = result.scalar_one_or_none()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    await db.delete(trigger)
    await db.commit()
    return {"deleted": True}


@router.get("/queue")
async def list_trigger_queue(
    status: str = "pending",
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(get_current_user),
):
    entries = await get_trigger_queue(db, status=status)
    return entries


@router.post("/queue/{queue_id}/approve")
async def approve_queue_entry(
    queue_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(get_current_user),
):
    try:
        entry = await approve_trigger(queue_id, db)
        await db.commit()
        return {"id": entry.id, "status": entry.status, "execution_run_id": entry.execution_run_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/queue/{queue_id}/reject")
async def reject_queue_entry(
    queue_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(get_current_user),
):
    try:
        entry = await reject_trigger(queue_id, db)
        await db.commit()
        return {"id": entry.id, "status": entry.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
