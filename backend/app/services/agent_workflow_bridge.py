import json
import logging
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.models.workflow import WorkflowTemplate, UserWorkflow

logger = logging.getLogger(__name__)


async def execute_agent_step(step_config: dict, user_context: dict, db: AsyncSession) -> dict:
    agent_id = step_config.get("agent_id", "")
    prompt_template = step_config.get("prompt", "")
    timeout_seconds = step_config.get("timeout", 60)

    user_id = user_context.get("user_id", "")
    user_msg = prompt_template
    for k, v in user_context.items():
        user_msg = user_msg.replace("{{" + k + "}}", str(v))

    try:
        from app.services.agent_runtime import execute_agent_run

        input_payload = {
            "message": user_msg,
            "user_id": user_id,
            "tenant_id": user_context.get("tenant_id", "unknown"),
        }

        result = await execute_agent_run(db, agent_id, input_payload, trigger_source="workflow_agent_step")

        return {
            "status": "completed",
            "output": result.get("reply", ""),
            "agent_run_id": result.get("run_id", ""),
            "latency_ms": result.get("latency_ms", 0),
        }
    except Exception as e:
        logger.error(f"Agent step execution failed: {e}")
        return {"status": "failed", "error": str(e), "output": ""}


async def trigger_workflow_from_agent(
    workflow_template_id: str,
    user_id: str,
    agent_context: dict,
    db: AsyncSession
) -> str:
    tmpl_res = await db.execute(select(WorkflowTemplate).where(WorkflowTemplate.id == workflow_template_id))
    template = tmpl_res.scalar_one_or_none()
    if not template:
        return json.dumps({"error": f"Workflow template {workflow_template_id} not found"})

    existing = await db.execute(
        select(UserWorkflow).where(
            UserWorkflow.user_id == user_id,
            UserWorkflow.template_id == workflow_template_id,
            UserWorkflow.status == "in_progress",
        )
    )
    if existing.scalar_one_or_none():
        return json.dumps({"error": f"User {user_id} already has an active workflow for template {workflow_template_id}", "status": "duplicate"})

    steps_default = {}
    for step in template.steps or []:
        sid = step.get("id", uuid.uuid4().hex)
        steps_default[sid] = {"completed": False, "completed_by": None, "completed_at": None}

    user_workflow = UserWorkflow(
        id=uuid.uuid4().hex,
        user_id=user_id,
        template_id=workflow_template_id,
        status="in_progress",
        steps_status=steps_default,
    )
    db.add(user_workflow)
    await db.commit()

    return json.dumps({
        "success": True,
        "workflow_id": user_workflow.id,
        "template_name": template.name,
        "template_type": template.type,
        "message": f"Workflow '{template.name}' started for user {user_id}",
    })


async def _tool_trigger_workflow(db: AsyncSession, user_id: str = "", workflow_template_id: str = "", template_name: str = "") -> str:
    try:
        if not workflow_template_id and template_name:
            tmpl_res = await db.execute(
                select(WorkflowTemplate).where(WorkflowTemplate.name.ilike(f"%{template_name}%"))
            )
            tmpl = tmpl_res.scalars().first()
            if tmpl:
                workflow_template_id = tmpl.id
            else:
                return json.dumps({"error": f"No workflow template matching '{template_name}' found"})

        if not workflow_template_id:
            return json.dumps({"error": "workflow_template_id or template_name required"})

        if not user_id:
            return json.dumps({"error": "user_id is required"})

        return await trigger_workflow_from_agent(workflow_template_id, user_id, {}, db)
    except Exception as e:
        logger.error(f"Error in trigger_workflow tool: {e}")
        return json.dumps({"error": str(e)})


async def _tool_complete_workflow_step(db: AsyncSession, workflow_id: str = "", step_id: str = "", completed_by: str = "") -> str:
    try:
        if not workflow_id or not step_id:
            return json.dumps({"error": "workflow_id and step_id are required"})

        result = await db.execute(select(UserWorkflow).where(UserWorkflow.id == workflow_id))
        uf = result.scalar_one_or_none()
        if not uf:
            return json.dumps({"error": f"Workflow {workflow_id} not found"})

        steps = uf.steps_status or {}
        if step_id not in steps:
            return json.dumps({"error": f"Step {step_id} not found in workflow {workflow_id}"})

        steps[step_id] = {
            "completed": True,
            "completed_by": completed_by,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        uf.steps_status = steps

        all_done = all(s.get("completed") for s in steps.values())
        if all_done:
            uf.status = "completed"

        await db.commit()

        return json.dumps({
            "success": True,
            "workflow_id": workflow_id,
            "step_id": step_id,
            "all_steps_completed": all_done,
            "workflow_status": uf.status,
        })
    except Exception as e:
        logger.error(f"Error in complete_workflow_step tool: {e}")
        return json.dumps({"error": str(e)})
