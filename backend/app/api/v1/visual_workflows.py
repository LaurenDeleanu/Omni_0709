from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import os
import uuid
import json
import hmac
import hashlib

from app.api.dependencies import get_tenant_db, require_roles
from app.core.config import settings
from app.models.visual_workflow import VisualWorkflow
from app.models.workflow_step import WorkflowStep
from app.models.workflow_trigger import WorkflowTrigger
from app.services.workflow_runtime import execute_workflow_run

router = APIRouter()


async def _verify_webhook_signature(request: Request):
    secret = os.getenv("WEBHOOK_SECRET", settings.SECRET_KEY)
    signature = request.headers.get("X-Hub-Signature")
    
    if not signature:
        token = request.headers.get("X-Webhook-Secret")
        if not token or token != secret:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret")
        return True

    body = await request.body()
    key = secret.encode("utf-8")
    computed_hash = hmac.new(key, body, hashlib.sha256).hexdigest()
    
    expected_signature = signature
    if signature.startswith("sha256="):
        expected_signature = signature[7:]
        
    if not hmac.compare_digest(computed_hash, expected_signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid HMAC signature")
    return True


# --- Workflow CRUD ---
class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    agent_id: Optional[str] = None

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    body: WorkflowCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    tenant_id = db.info.get("tenant_id")
    workflow = VisualWorkflow(
        id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        name=body.name,
        description=body.description,
        agent_id=body.agent_id
    )
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)
    return workflow

@router.get("")
async def list_workflows(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin", "employee"]))
):
    tenant_id = db.info.get("tenant_id")
    # db.info["tenant_id"] correctly has the context
    result = await db.execute(select(VisualWorkflow).where(VisualWorkflow.tenant_id == tenant_id))
    return {"workflows": result.scalars().all()}


# --- Workflow Steps ---
class StepIn(BaseModel):
    type: str
    label: str
    config: str = "{}"
    next_nodes: Optional[List[str]] = []
    condition: Optional[str] = None
    position: Optional[dict] = None

class StepsReorderIn(BaseModel):
    steps: list

def _step_to_dict(s: WorkflowStep) -> dict:
    return {
        "id": s.id, "type": s.type, "label": s.label,
        "config": s.config, "order": s.order,
        "next_nodes": s.next_nodes,
        "condition": s.condition,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


@router.get("/{workflow_id}/steps")
async def get_steps(
    workflow_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    wf_res = await db.execute(select(VisualWorkflow).where(VisualWorkflow.id == workflow_id))
    if not wf_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    result = await db.execute(
        select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id).order_by(WorkflowStep.order.asc())
    )
    steps = result.scalars().all()
    return {"steps": [_step_to_dict(s) for s in steps], "workflowId": workflow_id}


@router.post("/{workflow_id}/steps", status_code=status.HTTP_201_CREATED)
async def create_step(
    workflow_id: str,
    body: StepIn,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    wf_res = await db.execute(select(VisualWorkflow).where(VisualWorkflow.id == workflow_id))
    if not wf_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Workflow not found")

    max_order_result = await db.execute(
        select(WorkflowStep.order).where(WorkflowStep.workflow_id == workflow_id).order_by(WorkflowStep.order.desc()).limit(1)
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
        id=uuid.uuid4().hex, workflow_id=workflow_id, type=body.type,
        label=body.label, config=config, order=next_order,
        next_nodes=body.next_nodes or [], condition=body.condition
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return _step_to_dict(step)


@router.patch("/{workflow_id}/steps/{step_id}")
async def update_step(
    workflow_id: str,
    step_id: str,
    body: dict,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    result = await db.execute(
        select(WorkflowStep).where(WorkflowStep.id == step_id, WorkflowStep.workflow_id == workflow_id)
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


@router.put("/{workflow_id}/steps")
async def reorder_steps(
    workflow_id: str,
    body: StepsReorderIn,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    for item in body.steps:
        result = await db.execute(select(WorkflowStep).where(WorkflowStep.id == item["id"], WorkflowStep.workflow_id == workflow_id))
        step = result.scalar_one_or_none()
        if step:
            step.order = item.get("order", step.order)
    await db.commit()
    result = await db.execute(select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id).order_by(WorkflowStep.order.asc()))
    return {"steps": [_step_to_dict(s) for s in result.scalars().all()]}


@router.delete("/{workflow_id}/steps/{step_id}")
async def delete_step(
    workflow_id: str,
    step_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    result = await db.execute(
        select(WorkflowStep).where(WorkflowStep.id == step_id, WorkflowStep.workflow_id == workflow_id)
    )
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    deleted_order = step.order
    await db.delete(step)

    # Re-index remaining steps
    remaining = await db.execute(
        select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id, WorkflowStep.order > deleted_order).order_by(WorkflowStep.order.asc())
    )
    for s in remaining.scalars().all():
        s.order -= 1

    await db.commit()
    return {"status": "deleted", "id": step_id}


@router.post("/{workflow_id}/steps/{step_id}/duplicate", status_code=status.HTTP_201_CREATED)
async def duplicate_step(
    workflow_id: str,
    step_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    result = await db.execute(
        select(WorkflowStep).where(WorkflowStep.id == step_id, WorkflowStep.workflow_id == workflow_id)
    )
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Step not found")

    max_order_result = await db.execute(
        select(WorkflowStep.order).where(WorkflowStep.workflow_id == workflow_id).order_by(WorkflowStep.order.desc()).limit(1)
    )
    next_order = (max_order_result.scalar() or 0) + 1

    # Offset the position so the duplicate doesn't stack exactly on top
    config = original.config or "{}"
    try:
        cfg = json.loads(config)
        if "position" in cfg:
            cfg["position"] = {"x": cfg["position"].get("x", 0) + 40, "y": cfg["position"].get("y", 0) + 40}
        config = json.dumps(cfg)
    except Exception:
        pass

    clone = WorkflowStep(
        id=uuid.uuid4().hex,
        workflow_id=workflow_id,
        type=original.type,
        label=f"{original.label} (copia)",
        config=config,
        order=next_order,
        next_nodes=[],
        condition=original.condition,
    )
    db.add(clone)
    await db.commit()
    await db.refresh(clone)
    return _step_to_dict(clone)


# --- Triggers ---
class TriggerIn(BaseModel):
    type: str = "MANUAL"
    config: str = "{}"


@router.get("/{workflow_id}/triggers")
async def get_triggers(
    workflow_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    result = await db.execute(
        select(WorkflowTrigger).where(WorkflowTrigger.workflow_id == workflow_id).order_by(WorkflowTrigger.created_at.desc())
    )
    triggers = result.scalars().all()
    return {"triggers": [{"id": t.id, "type": t.type, "config": t.config, "enabled": t.enabled,
            "last_triggered_at": t.last_triggered_at.isoformat() if t.last_triggered_at else None,
            "created_at": t.created_at.isoformat()} for t in triggers]}


@router.post("/{workflow_id}/triggers", status_code=status.HTTP_201_CREATED)
async def create_trigger(
    workflow_id: str,
    body: TriggerIn,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    trigger = WorkflowTrigger(
        id=uuid.uuid4().hex, workflow_id=workflow_id, type=body.type, config=body.config,
    )
    db.add(trigger)
    await db.commit()
    await db.refresh(trigger)
    return {"id": trigger.id, "type": trigger.type, "config": trigger.config, "enabled": trigger.enabled}


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    body: dict,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    message = body.get("message", "init_workflow")
    collected = body.get("collectedData")
    step_id = body.get("currentStepId")
    # Note: workflow_runtime.py execute_workflow_run will be updated to accept workflow_id instead of bot_id
    result = await execute_workflow_run(db, workflow_id, message, collected, step_id)
    return result


@router.post("/triggers/webhook/{trigger_id}")
async def webhook_trigger(
    trigger_id: str,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
):
    await _verify_webhook_signature(request)
    result = await db.execute(select(WorkflowTrigger).where(WorkflowTrigger.id == trigger_id))
    trigger = result.scalar_one_or_none()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    if not trigger.enabled:
        raise HTTPException(status_code=400, detail="Trigger is disabled")

    from datetime import timezone as tz
    from datetime import datetime as dt
    trigger.last_triggered_at = dt.now(tz.utc)

    # Note: execute_workflow_run expects workflow_id now
    result = await execute_workflow_run(db, trigger.workflow_id, "webhook_trigger", body.get("payload", {}))
    await db.commit()
    return result
