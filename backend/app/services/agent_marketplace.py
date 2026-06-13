import logging
import asyncio
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.agent_reputation import get_cached_reputation

logger = logging.getLogger("successcore.marketplace")


async def get_marketplace_agents(db: AsyncSession) -> List[Dict]:
    from app.models.agent import Agent

    result = await db.execute(
        select(Agent).order_by(Agent.created_at.desc()).limit(50)
    )
    agents = result.scalars().all()

    reputations = await asyncio.gather(
        *[get_cached_reputation(a.id) for a in agents],
        return_exceptions=True,
    )
    rep_map = {}
    for a, rep in zip(agents, reputations):
        if isinstance(rep, Exception):
            rep_map[a.id] = None
        else:
            rep_map[a.id] = rep

    marketplace = []
    for a in agents:
        tools_raw = a.agent_settings.get("ai_tools") if a.agent_settings else "[]"
        import json
        try:
            tools = json.loads(tools_raw) if isinstance(tools_raw, str) else tools_raw
        except (json.JSONDecodeError, TypeError):
            tools = []

        rep = rep_map.get(a.id)
        badge = "new"
        if rep:
            score = rep.get("overall_score", 50)
            if score >= 85:
                badge = "elite"
            elif score >= 70:
                badge = "trusted"
            elif score >= 50:
                badge = "standard"

        marketplace.append({
            "id": a.id,
            "name": a.name,
            "avatar": a.avatar,
            "agent_type": a.agent_type,
            "ai_model": a.ai_model,
            "ai_temperature": a.ai_temperature,
            "ai_tone": a.ai_tone,
            "tools": tools,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "install_url": f"/api/v1/agents/{a.id}/export",
            "reputation_badge": badge,
            "reputation_score": rep.get("overall_score") if rep else None,
        })

    return marketplace
