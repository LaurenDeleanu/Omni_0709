from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel
import os

from app.api.dependencies import get_tenant_db, require_roles
from app.core.config import settings
from app.models.agent import Agent
from app.models.workflow_step import WorkflowStep
from app.models.workflow_trigger import WorkflowTrigger


def _verify_webhook_signature(request: Request):
    secret = os.getenv("WEBHOOK_SECRET", settings.SECRET_KEY)
    token = request.headers.get("X-Webhook-Secret") or request.headers.get("X-Hub-Signature")
    if not token or token != secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret")
    return True
from app.services.workflow_runtime import execute_workflow_run
from app.services.workflow_export_import import export_workflow, import_workflow
import uuid
import json

router = APIRouter()


class StepIn(BaseModel):
    type: str
    label: str
    config: str = "{}"
    position: Optional[dict] = None


class StepsReorderIn(BaseModel):
    steps: list


def _step_to_dict(s: WorkflowStep) -> dict:
    return {
        "id": s.id, "type": s.type, "label": s.label,
        "config": s.config, "order": s.order,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


@router.get("/{bot_id}/steps")
async def get_steps(
    bot_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    agent_res = await db.execute(select(Agent).where(Agent.id == bot_id))
    if not agent_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")
    result = await db.execute(
        select(WorkflowStep).where(WorkflowStep.bot_id == bot_id).order_by(WorkflowStep.order.asc())
    )
    steps = result.scalars().all()
    return {"steps": [_step_to_dict(s) for s in steps], "botId": bot_id}


@router.post("/{bot_id}/steps", status_code=status.HTTP_201_CREATED)
async def create_step(
    bot_id: str,
    body: StepIn,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    agent_res = await db.execute(select(Agent).where(Agent.id == bot_id))
    if not agent_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")

    max_order_result = await db.execute(
        select(WorkflowStep.order).where(WorkflowStep.bot_id == bot_id).order_by(WorkflowStep.order.desc()).limit(1)
    )
    next_order = (max_order_result.scalar() or 0) + 1

    config = body.config
    if body.position:
        try:
            cfg = json.loads(config)
            cfg["position"] = body.position
            config = json.dumps(cfg)
        except Exception:
            pass

    step = WorkflowStep(
        id=uuid.uuid4().hex, bot_id=bot_id, type=body.type,
        label=body.label, config=config, order=next_order,
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return _step_to_dict(step)


@router.patch("/{bot_id}/steps/{step_id}")
async def update_step(
    bot_id: str,
    step_id: str,
    body: dict,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    result = await db.execute(
        select(WorkflowStep).where(WorkflowStep.id == step_id, WorkflowStep.bot_id == bot_id)
    )
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    for key, value in body.items():
        if hasattr(step, key):
            setattr(step, key, value)
    await db.commit()
    await db.refresh(step)
    return _step_to_dict(step)


@router.put("/{bot_id}/steps")
async def reorder_steps(
    bot_id: str,
    body: StepsReorderIn,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    for item in body.steps:
        result = await db.execute(select(WorkflowStep).where(WorkflowStep.id == item["id"], WorkflowStep.bot_id == bot_id))
        step = result.scalar_one_or_none()
        if step:
            step.order = item.get("order", step.order)
    await db.commit()
    result = await db.execute(select(WorkflowStep).where(WorkflowStep.bot_id == bot_id).order_by(WorkflowStep.order.asc()))
    return {"steps": [_step_to_dict(s) for s in result.scalars().all()]}


@router.delete("/{bot_id}/steps/{step_id}")
async def delete_step(
    bot_id: str,
    step_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    result = await db.execute(
        select(WorkflowStep).where(WorkflowStep.id == step_id, WorkflowStep.bot_id == bot_id)
    )
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    deleted_order = step.order
    await db.delete(step)

    # Re-index remaining steps
    remaining = await db.execute(
        select(WorkflowStep).where(WorkflowStep.bot_id == bot_id, WorkflowStep.order > deleted_order).order_by(WorkflowStep.order.asc())
    )
    for s in remaining.scalars().all():
        s.order -= 1

    await db.commit()
    return {"status": "deleted", "id": step_id}


@router.post("/{bot_id}/steps/{step_id}/duplicate")
async def duplicate_step(
    bot_id: str,
    step_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    result = await db.execute(
        select(WorkflowStep).where(WorkflowStep.id == step_id, WorkflowStep.bot_id == bot_id)
    )
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Step not found")

    max_order_result = await db.execute(
        select(WorkflowStep.order).where(WorkflowStep.bot_id == bot_id).order_by(WorkflowStep.order.desc()).limit(1)
    )
    next_order = (max_order_result.scalar() or 0) + 1

    copy = WorkflowStep(
        id=uuid.uuid4().hex, bot_id=bot_id, type=original.type,
        label=f"{original.label} (copia)", config=original.config, order=next_order,
    )
    db.add(copy)
    await db.commit()
    await db.refresh(copy)
    return _step_to_dict(copy)


@router.get("/{bot_id}/products")
async def get_products(
    bot_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    result = await db.execute(
        select(WorkflowStep).where(WorkflowStep.bot_id == bot_id, WorkflowStep.type == "SHOW_PRODUCTS").order_by(WorkflowStep.order.asc())
    )
    products = result.scalars().all()
    return {"products": [{"id": s.id, "label": s.label, "config": s.config} for s in products]}


@router.get("/schedules")
async def get_schedules(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    result = await db.execute(
        select(WorkflowStep).where(WorkflowStep.type == "SCHEDULE").order_by(WorkflowStep.order.desc()).limit(20)
    )
    schedules = result.scalars().all()
    schedule_list = [{"id": s.id, "label": s.label, "config": s.config, "bot_id": s.bot_id} for s in schedules]
    schedule_list.append({"id": "google_calendar", "label": "Google Calendar", "config": "{}", "bot_id": ""})
    schedule_list.append({"id": "outlook_calendar", "label": "Outlook Calendar", "config": "{}", "bot_id": ""})
    return {"schedules": schedule_list}


class TriggerIn(BaseModel):
    type: str = "MANUAL"
    config: str = "{}"


@router.get("/{bot_id}/triggers")
async def get_triggers(
    bot_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    result = await db.execute(
        select(WorkflowTrigger).where(WorkflowTrigger.bot_id == bot_id).order_by(WorkflowTrigger.created_at.desc())
    )
    triggers = result.scalars().all()
    return {"triggers": [{"id": t.id, "type": t.type, "config": t.config, "enabled": t.enabled,
            "last_triggered_at": t.last_triggered_at.isoformat() if t.last_triggered_at else None,
            "created_at": t.created_at.isoformat()} for t in triggers]}


@router.post("/{bot_id}/triggers", status_code=status.HTTP_201_CREATED)
async def create_trigger(
    bot_id: str,
    body: TriggerIn,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    trigger = WorkflowTrigger(
        id=uuid.uuid4().hex, bot_id=bot_id, type=body.type, config=body.config,
    )
    db.add(trigger)
    await db.commit()
    await db.refresh(trigger)
    return {"id": trigger.id, "type": trigger.type, "config": trigger.config, "enabled": trigger.enabled}


@router.patch("/{bot_id}/triggers/{trigger_id}")
async def update_trigger(
    bot_id: str,
    trigger_id: str,
    body: dict,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    result = await db.execute(select(WorkflowTrigger).where(WorkflowTrigger.id == trigger_id))
    trigger = result.scalar_one_or_none()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    if "enabled" in body:
        trigger.enabled = body["enabled"]
    if "config" in body:
        trigger.config = body["config"]
    await db.commit()
    return {"status": "updated"}


@router.delete("/{bot_id}/triggers/{trigger_id}")
async def delete_trigger(
    bot_id: str,
    trigger_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    result = await db.execute(select(WorkflowTrigger).where(WorkflowTrigger.id == trigger_id))
    trigger = result.scalar_one_or_none()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    await db.delete(trigger)
    await db.commit()
    return {"status": "deleted"}


@router.post("/{bot_id}/execute")
async def execute_workflow(
    bot_id: str,
    body: dict,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    message = body.get("message", "init_workflow")
    collected = body.get("collectedData")
    step_id = body.get("currentStepId")
    result = await execute_workflow_run(db, bot_id, message, collected, step_id)
    return result


@router.get("/{bot_id}/runs")
async def get_workflow_runs(
    bot_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.models.agent import AgentExecutionRun
    result = await db.execute(
        select(AgentExecutionRun).where(AgentExecutionRun.agent_id == bot_id).order_by(AgentExecutionRun.created_at.desc()).limit(50)
    )
    runs = result.scalars().all()
    return {"runs": [{"id": r.id, "status": r.status, "cost_usd": r.cost_usd,
            "created_at": r.created_at.isoformat() if r.created_at else None} for r in runs]}


@router.post("/triggers/webhook/{trigger_id}")
async def webhook_trigger(
    trigger_id: str,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
):
    _verify_webhook_signature(request)
    result = await db.execute(select(WorkflowTrigger).where(WorkflowTrigger.id == trigger_id))
    trigger = result.scalar_one_or_none()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    if not trigger.enabled:
        raise HTTPException(status_code=400, detail="Trigger is disabled")

    from datetime import timezone as tz
    from datetime import datetime as dt
    trigger.last_triggered_at = dt.now(tz.utc)

    from app.services.workflow_runtime import execute_workflow_run
    result = await execute_workflow_run(db, trigger.bot_id, "webhook_trigger", body.get("payload", {}))
    await db.commit()
    return result
