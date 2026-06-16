import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.workflow_step import WorkflowStep

logger = logging.getLogger("successcore.branching")


async def resolve_next_step(
    db: AsyncSession, workflow_id: str, current_step: dict, collected_data: dict,
) -> Optional[dict]:
    config = current_step.get("config")
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except json.JSONDecodeError:
            config = {}
    step_type = current_step.get("type", "")

    # 1. New DAG logic: evaluate next_nodes using condition
    next_nodes = current_step.get("next_nodes", [])
    if next_nodes:
        # If there's a condition and multiple next nodes, we can use the condition result to route.
        # But for now, we just pick the first valid node in the next_nodes array.
        # In a fully fleshed out DAG, we would evaluate edges.
        target_id = next_nodes[0]
        if target_id:
            result = await db.execute(select(WorkflowStep).where(WorkflowStep.id == target_id, WorkflowStep.workflow_id == workflow_id))
            step = result.scalar_one_or_none()
            if step:
                return {"id": step.id, "type": step.type, "label": step.label, "config": step.config, "order": step.order, "next_nodes": step.next_nodes}

    # 2. Autonomous agent transition
    if step_type == "AUTONOMOUS_AGENT" and collected_data.get("_transition"):
        transition_id = collected_data["_transition"]
        result = await db.execute(select(WorkflowStep).where(WorkflowStep.id == transition_id, WorkflowStep.workflow_id == workflow_id))
        step = result.scalar_one_or_none()
        if step:
            return {"id": step.id, "type": step.type, "label": step.label, "config": step.config, "order": step.order, "next_nodes": step.next_nodes}

    # 3. Branch evaluation (legacy config support)
    branches = config.get("branches", [])
    if isinstance(branches, list) and branches:
        check_field = config.get("checkField") or config.get("field")
        check_value = collected_data.get(check_field, "") if check_field else ""

        for branch in branches:
            match_rule = str(branch.get("match", "")).strip()
            if not match_rule:
                continue
            try:
                import re
                if match_rule == check_value or re.match(match_rule, str(check_value), re.IGNORECASE):
                    target_id = branch.get("goToStepId")
                    target_order = branch.get("goToStepOrder")
                    if target_id:
                        result = await db.execute(select(WorkflowStep).where(WorkflowStep.id == target_id, WorkflowStep.workflow_id == workflow_id))
                        step = result.scalar_one_or_none()
                        if step:
                            return {"id": step.id, "type": step.type, "label": step.label, "config": step.config, "order": step.order, "next_nodes": step.next_nodes}
                    elif target_order:
                        result = await db.execute(select(WorkflowStep).where(WorkflowStep.order == target_order, WorkflowStep.workflow_id == workflow_id))
                        step = result.scalar_one_or_none()
                        if step:
                            return {"id": step.id, "type": step.type, "label": step.label, "config": step.config, "order": step.order, "next_nodes": step.next_nodes}
            except Exception:
                pass

    # 4. AB Test
    if step_type == "AB_TEST":
        import random
        branch_key = "branchAStepId" if random.random() < (config.get("branchAWeight", 50) / 100) else "branchBStepId"
        target_id = config.get(branch_key)
        if target_id:
            result = await db.execute(select(WorkflowStep).where(WorkflowStep.id == target_id, WorkflowStep.workflow_id == workflow_id))
            step = result.scalar_one_or_none()
            if step:
                return {"id": step.id, "type": step.type, "label": step.label, "config": step.config, "order": step.order, "next_nodes": step.next_nodes}

    # 5. Visual nextStepId (legacy canvas config)
    next_id = config.get("nextStepId")
    if next_id:
        result = await db.execute(select(WorkflowStep).where(WorkflowStep.id == next_id, WorkflowStep.workflow_id == workflow_id))
        step = result.scalar_one_or_none()
        if step:
            return {"id": step.id, "type": step.type, "label": step.label, "config": step.config, "order": step.order, "next_nodes": step.next_nodes}

    # 6. Linear next (fallback)
    current_order = current_step.get("order", 0)
    result = await db.execute(
        select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id, WorkflowStep.order > current_order).order_by(WorkflowStep.order.asc()).limit(1)
    )
    step = result.scalar_one_or_none()
    if step:
        return {"id": step.id, "type": step.type, "label": step.label, "config": step.config, "order": step.order, "next_nodes": step.next_nodes}

    return None
