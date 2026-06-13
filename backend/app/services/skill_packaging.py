import json
import logging
import zipfile
import io
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger("successcore.skills_packaging")


async def export_agent_package(db: AsyncSession, agent_id: str) -> bytes:
    from app.models.agent import Agent, AgentConfig

    agent_res = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_res.scalar_one_or_none()
    if not agent:
        raise ValueError("Agent not found")

    config_res = await db.execute(select(AgentConfig).where(AgentConfig.agent_id == agent_id))
    config = config_res.scalar_one_or_none()

    package = {
        "version": "1.0",
        "type": "agent_skill_package",
        "agent": {
            "name": agent.name,
            "avatar": agent.avatar,
            "agent_type": agent.agent_type,
            "ai_model": agent.ai_model,
            "ai_system_prompt": agent.ai_system_prompt,
            "ai_temperature": agent.ai_temperature,
            "ai_tone": agent.ai_tone,
            "ai_guardrails": agent.ai_guardrails,
            "ai_fallback_models": agent.agent_settings.get("ai_fallback_models") if agent.agent_settings else None,
            "ai_tools": agent.agent_settings.get("ai_tools") if agent.agent_settings else [],
        },
        "config": {
            "max_loops": config.max_loops if config else 10,
            "max_tokens_per_run": config.max_tokens_per_run if config else 50000,
        },
        "exported_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"agent_{agent.name.lower().replace(' ', '_')}/package.json",
                     json.dumps(package, ensure_ascii=False, indent=2))
    buf.seek(0)
    return buf.read()


async def import_agent_package(db: AsyncSession, package_json: str) -> dict:
    import uuid

    package = json.loads(package_json)
    agent_data = package.get("agent", {})
    config_data = package.get("config", {})

    from app.models.agent import Agent, AgentConfig

    new_agent = Agent(
        id=uuid.uuid4().hex,
        name=agent_data.get("name", "Imported Agent"),
        avatar=agent_data.get("avatar"),
        agent_type=agent_data.get("agent_type"),
        ai_model=agent_data.get("ai_model", "gpt-4o-mini"),
        ai_system_prompt=agent_data.get("ai_system_prompt", ""),
        ai_temperature=agent_data.get("ai_temperature", 0.5),
        ai_tone=agent_data.get("ai_tone"),
        ai_guardrails=agent_data.get("ai_guardrails"),
        agent_settings={
            "ai_fallback_models": agent_data.get("ai_fallback_models"),
            "ai_tools": json.dumps(agent_data.get("ai_tools", [])),
        },
    )
    db.add(new_agent)
    await db.flush()

    new_config = AgentConfig(
        id=uuid.uuid4().hex,
        agent_id=new_agent.id,
        max_loops=config_data.get("max_loops", 10),
        max_tokens_per_run=config_data.get("max_tokens_per_run", 50000),
    )
    db.add(new_config)
    await db.commit()
    await db.refresh(new_agent)

    return {"id": new_agent.id, "name": new_agent.name, "status": "imported"}
