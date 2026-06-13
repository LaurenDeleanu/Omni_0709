import json
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger("successcore.workflow_export")


async def export_workflow(db: AsyncSession, bot_id: str) -> dict:
    from app.models.agent import Agent, AgentConfig
    from app.models.workflow_step import WorkflowStep
    from app.models.workflow_trigger import WorkflowTrigger

    agent_res = await db.execute(select(Agent).where(Agent.id == bot_id))
    agent = agent_res.scalar_one_or_none()
    if not agent:
        raise ValueError("Agent not found")

    config_res = await db.execute(select(AgentConfig).where(AgentConfig.agent_id == bot_id))
    config = config_res.scalar_one_or_none()

    steps_res = await db.execute(
        select(WorkflowStep).where(WorkflowStep.bot_id == bot_id).order_by(WorkflowStep.order.asc())
    )
    steps = steps_res.scalars().all()

    triggers_res = await db.execute(select(WorkflowTrigger).where(WorkflowTrigger.bot_id == bot_id))
    triggers = triggers_res.scalars().all()

    return {
        "version": "2.0",
        "type": "workflow_package",
        "agent": {
            "name": agent.name,
            "agent_type": agent.agent_type,
            "ai_model": agent.ai_model,
            "ai_system_prompt": agent.ai_system_prompt,
            "ai_temperature": agent.ai_temperature,
            "ai_tone": agent.ai_tone,
        },
        "config": {
            "max_loops": config.max_loops if config else 10,
            "max_tokens_per_run": config.max_tokens_per_run if config else 50000,
        },
        "steps": [
            {"type": s.type, "label": s.label, "config": s.config, "order": s.order}
            for s in steps
        ],
        "triggers": [
            {"type": t.type, "config": t.config, "enabled": t.enabled}
            for t in triggers
        ],
    }


async def import_workflow(db: AsyncSession, package: dict) -> dict:
    import uuid
    from app.models.agent import Agent, AgentConfig
    from app.models.workflow_step import WorkflowStep
    from app.models.workflow_trigger import WorkflowTrigger

    agent_data = package.get("agent", {})
    config_data = package.get("config", {})
    steps_data = package.get("steps", [])
    triggers_data = package.get("triggers", [])

    agent = Agent(
        id=uuid.uuid4().hex,
        name=agent_data.get("name", "Imported Workflow"),
        agent_type=agent_data.get("agent_type", "WORKFLOW"),
        ai_model=agent_data.get("ai_model", "gpt-4o-mini"),
        ai_system_prompt=agent_data.get("ai_system_prompt", ""),
        ai_temperature=agent_data.get("ai_temperature", 0.5),
        ai_tone=agent_data.get("ai_tone"),
    )
    db.add(agent)
    await db.flush()

    config = AgentConfig(
        id=uuid.uuid4().hex,
        agent_id=agent.id,
        max_loops=config_data.get("max_loops", 10),
        max_tokens_per_run=config_data.get("max_tokens_per_run", 50000),
    )
    db.add(config)

    for step in steps_data:
        db.add(WorkflowStep(
            id=uuid.uuid4().hex, bot_id=agent.id,
            type=step["type"], label=step["label"],
            config=step.get("config", "{}"), order=step.get("order", 0),
        ))

    for trigger in triggers_data:
        db.add(WorkflowTrigger(
            id=uuid.uuid4().hex, bot_id=agent.id,
            type=trigger["type"], config=trigger.get("config", "{}"),
            enabled=trigger.get("enabled", True),
        ))

    await db.commit()
    await db.refresh(agent)
    return {"id": agent.id, "name": agent.name, "steps_count": len(steps_data), "triggers_count": len(triggers_data)}
