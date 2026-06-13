from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from pydantic import BaseModel

from app.api.dependencies import get_tenant_db, require_roles, get_current_user
from app.models.agent import AgentSchedule
from app.services.agent_scheduler import check_due_schedules, _next_run_from_cron
from app.services.agent_runtime import execute_agent_run
import uuid

router = APIRouter()


class ScheduleCreate(BaseModel):
    agent_id: str
    name: str
    cron_expression: str
    input_template: str
    input_variables: dict = None
    is_active: bool = True


class ScheduleUpdate(BaseModel):
    name: str = None
    cron_expression: str = None
    input_template: str = None
    input_variables: dict = None
    is_active: bool = None


@router.get("/")
async def list_schedules(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(AgentSchedule).order_by(AgentSchedule.created_at.desc())
    )
    schedules = result.scalars().all()
    return [
        {
            "id": s.id,
            "agent_id": s.agent_id,
            "name": s.name,
            "cron_expression": s.cron_expression,
            "input_template": s.input_template,
            "input_variables": s.input_variables,
            "is_active": s.is_active,
            "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
            "last_run_status": s.last_run_status,
            "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in schedules
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_schedule(
    body: ScheduleCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    sched = AgentSchedule(
        id=uuid.uuid4().hex,
        agent_id=body.agent_id,
        name=body.name,
        cron_expression=body.cron_expression,
        input_template=body.input_template,
        input_variables=body.input_variables,
        is_active=body.is_active,
        next_run_at=_next_run_from_cron(body.cron_expression, now),
    )
    db.add(sched)
    await db.commit()
    await db.refresh(sched)
    return {
        "id": sched.id,
        "agent_id": sched.agent_id,
        "name": sched.name,
        "cron_expression": sched.cron_expression,
        "is_active": sched.is_active,
        "next_run_at": sched.next_run_at.isoformat() if sched.next_run_at else None,
    }


@router.put("/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    body: ScheduleUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(AgentSchedule).where(AgentSchedule.id == schedule_id)
    )
    sched = result.scalar_one_or_none()
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if body.name is not None:
        sched.name = body.name
    if body.cron_expression is not None:
        sched.cron_expression = body.cron_expression
        sched.next_run_at = _next_run_from_cron(body.cron_expression, datetime.now(timezone.utc))
    if body.input_template is not None:
        sched.input_template = body.input_template
    if body.input_variables is not None:
        sched.input_variables = body.input_variables
    if body.is_active is not None:
        sched.is_active = body.is_active

    await db.commit()
    await db.refresh(sched)
    return {"id": sched.id, "name": sched.name, "is_active": sched.is_active}


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(AgentSchedule).where(AgentSchedule.id == schedule_id)
    )
    sched = result.scalar_one_or_none()
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await db.delete(sched)
    await db.commit()
    return {"deleted": True}


@router.post("/{schedule_id}/run-now")
async def run_schedule_now(
    schedule_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(AgentSchedule).where(AgentSchedule.id == schedule_id)
    )
    sched = result.scalar_one_or_none()
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    run_result = await execute_agent_run(
        db=db,
        agent_id=sched.agent_id,
        input_payload={"message": sched.input_template, "user_id": "system"},
        trigger_source="cron",
    )
    sched.last_run_at = datetime.now(timezone.utc)
    sched.last_run_status = run_result.get("status", "success")
    await db.commit()
    return {"run_id": run_result.get("run_id"), "status": run_result.get("status")}
