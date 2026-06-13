import json
import logging
import asyncio
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.workflow_step import WorkflowStep
from app.models.workflow_trigger import WorkflowTrigger

logger = logging.getLogger("successcore.workflow_runtime")

TRANSPARENT_STEPS = {
    "CONDITION", "API_CALL", "AB_TEST", "ADD_TO_CART", "CREATE_LEAD",
    "HUMAN_TAKEOVER", "CALL_WORKFLOW", "CRM_ACTION", "DATA_TRANSFORM",
    "CODE_GENERATE", "GIT_COMMIT", "APPROVAL_GATE", "AI_DECISION", "NOTIFICATION",
}


async def _execute_transparent_step(step: dict, collected_data: dict) -> dict:
    step_type = step.get("type", "")
    config = step.get("config", {})
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except json.JSONDecodeError:
            config = {}

    if step_type == "API_CALL":
        try:
            import httpx
            url = config.get("apiUrl", "")
            method = config.get("apiMethod", "POST")
            body = config.get("apiBody", "{}")
            async with httpx.AsyncClient(timeout=30) as client:
                if method.upper() == "GET":
                    resp = await client.get(url)
                else:
                    resp = await client.post(url, content=body)
                collected_data[f"_api_response_{step['id']}"] = resp.text[:500]
                return {"status": "completed", "data": collected_data}
        except Exception as e:
            logger.warning(f"API_CALL failed: {e}")
            return {"status": "completed", "data": collected_data}

    if step_type == "NOTIFICATION":
        try:
            from app.services.email_service import send_email
            to = config.get("to", "")
            subject = config.get("subject", "Workflow Notification")
            body = config.get("body", str(collected_data.get("_initial_message", "")))
            await send_email(to, subject, body)
            collected_data["_notified"] = True
            return {"status": "completed", "data": collected_data}
        except Exception:
            return {"status": "completed", "data": collected_data}

    if step_type == "DATA_TRANSFORM":
        field = config.get("field", "")
        template = config.get("template", "{{input}}")
        value = collected_data.get(field, "")
        collected_data[field + "_transformed"] = template.replace("{{input}}", str(value))
        return {"status": "completed", "data": collected_data}

    if step_type == "CONDITION":
        field = config.get("checkField", config.get("field", ""))
        operator = config.get("operator", "==")
        value = config.get("value", "")
        actual = collected_data.get(field, "")
        collected_data["_condition_result"] = (str(actual) == str(value)) if operator == "==" else (str(actual) != str(value))
        return {"status": "completed", "data": collected_data}

    if step_type == "HUMAN_TAKEOVER":
        collected_data["_takeover"] = True
        return {"status": "paused", "data": collected_data}

    return {"status": "completed", "data": collected_data}


async def execute_workflow_run(
    db: AsyncSession,
    bot_id: str,
    input_message: str,
    collected_data: Optional[dict] = None,
    current_step_id: Optional[str] = None,
) -> dict:
    from app.services.branching import resolve_next_step

    data = collected_data or {}
    data["_initial_message"] = input_message

    # Load the starting step
    if current_step_id:
        result = await db.execute(
            select(WorkflowStep).where(WorkflowStep.id == current_step_id, WorkflowStep.bot_id == bot_id)
        )
        step = result.scalar_one_or_none()
    else:
        result = await db.execute(
            select(WorkflowStep).where(WorkflowStep.bot_id == bot_id).order_by(WorkflowStep.order.asc()).limit(1)
        )
        step = result.scalar_one_or_none()

    if not step:
        return {"status": "no_steps", "message": "No steps defined for this workflow"}

    trace = []
    max_iterations = 50
    iteration = 0

    current = {"id": step.id, "type": step.type, "label": step.label, "config": step.config, "order": step.order}

    while current and iteration < max_iterations:
        iteration += 1
        step_type = current.get("type", "")
        step_config = current.get("config", {})
        if isinstance(step_config, str):
            try:
                step_config = json.loads(step_config)
            except Exception:
                step_config = {}

        step_timeout = step_config.get("timeout", DEFAULT_TIMEOUT)
        step_start = datetime.now(timezone.utc)

        try:
            if step_type in TRANSPARENT_STEPS:
                result = await asyncio.wait_for(
                    _execute_transparent_step(current, data),
                    timeout=step_timeout
                )
                data = result.get("data", data)
                if result.get("status") == "paused":
                    trace.append({
                        "step_id": current["id"], "type": step_type, "action": "paused",
                        "duration_ms": int((datetime.now(timezone.utc) - step_start).total_seconds() * 1000),
                        "timeout_used": step_timeout
                    })
                    return {"status": "paused", "step_id": current["id"], "data": data, "trace": trace}
        except asyncio.TimeoutError:
            trace.append({
                "step_id": current["id"], "type": step_type, "action": "timeout",
                "duration_ms": step_timeout * 1000,
                "timeout_used": step_timeout
            })

        trace.append({
            "step_id": current["id"], "type": step_type, "action": "visited",
            "duration_ms": int((datetime.now(timezone.utc) - step_start).total_seconds() * 1000),
        })
        next_step = await resolve_next_step(db, bot_id, current, data)
        current = next_step

    status = "completed" if current is None else "max_iterations"
    return {"status": status, "data": data, "trace": trace, "iterations": iteration}
