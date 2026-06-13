import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone

from app.models.agent import Agent, AgentExecutionRun
from app.services.agent_reputation import get_cached_reputation

logger = logging.getLogger("successcore.agent_directory")


async def discover_agents(db: AsyncSession) -> List[Dict[str, Any]]:
    result = await db.execute(select(Agent).where(Agent.is_active == True))
    agents = list(result.scalars().all())

    profiles = []

    for agent in agents:
        run_stmt = (
            select(
                func.count(AgentExecutionRun.id).label("total"),
                func.avg(AgentExecutionRun.latency_ms).label("avg_latency"),
                func.avg(AgentExecutionRun.cost_usd).label("avg_cost"),
                func.sum(
                    func.case(
                        (AgentExecutionRun.status == "success", 1),
                        else_=0,
                    )
                ).label("successes"),
            )
            .where(AgentExecutionRun.agent_id == agent.id)
        )
        run_result = await db.execute(run_stmt)
        row = run_result.one_or_none()

        total_runs = int(row.total or 0)
        successes = int(row.successes or 0)
        success_rate = round(successes / total_runs, 4) if total_runs > 0 else 1.0
        avg_latency = int(round(row.avg_latency or 0))
        avg_cost = round(float(row.avg_cost or 0), 4)

        capabilities = []
        agent_settings = agent.agent_settings or {}
        description = agent_settings.get("description", "")
        if description:
            capabilities.append(description[:120])

        settings = agent.agent_settings or {}
        tools = []
        raw_tools = settings.get("ai_tools", settings.get("available_tools", []))
        if isinstance(raw_tools, list):
            tools = raw_tools[:10]
        elif isinstance(raw_tools, str):
            try:
                import json
                parsed = json.loads(raw_tools)
                if isinstance(parsed, list):
                    tools = parsed[:10]
            except Exception:
                pass

        fallback_models = settings.get("ai_fallback_models", ["gpt-4o-mini"])
        if isinstance(fallback_models, list):
            fallback_models = fallback_models[:3]

        rep = await get_cached_reputation(agent.id)
        reputation = {
            "overall_score": rep.get("overall_score", 50.0) if rep else 50.0,
            "trend": rep.get("trend", "stable") if rep else "stable",
        }

        profile = {
            "agent_id": agent.id,
            "name": agent.name,
            "agent_type": agent.agent_type,
            "capabilities": capabilities or [agent.agent_type],
            "tools": tools,
            "success_rate": success_rate,
            "avg_response_time_ms": avg_latency,
            "avg_cost_per_query": avg_cost,
            "is_available": agent.is_active,
            "handoff_supported": agent.agent_type in ("omni_master", "conversational"),
            "supports_streaming": True,
            "reputation": reputation,
            "model": {
                "primary": agent.ai_model,
                "fallback": fallback_models,
            },
            "health": {
                "status": "healthy",
                "last_checked": datetime.now(timezone.utc).isoformat(),
                "consecutive_failures": 0,
            },
        }
        profiles.append(profile)

    logger.info(f"Agent directory: discovered {len(profiles)} active agents")
    return profiles


async def standardize_agent_output(
    agent_id: str,
    raw_result: str,
    metadata: dict,
    db: AsyncSession,
) -> Dict[str, Any]:
    agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_result.scalar_one_or_none()

    agent_name = agent.name if agent else "Unknown"
    agent_type = agent.agent_type if agent else "unknown"

    tool_calls_made = metadata.get("tool_calls_made", 0)
    tools_used = metadata.get("tools_used", [])
    tokens = metadata.get("tokens_used", {"input": 0, "output": 0})
    cost = metadata.get("cost", {"total_usd": 0.0})
    latency = metadata.get("latency", {"total_ms": 0})
    model = metadata.get("model_used", agent.ai_model if agent else "unknown")
    provider = metadata.get("provider", "openai")
    trace = metadata.get("trace", [])
    warnings_list = metadata.get("warnings", [])
    suggestions = metadata.get("suggestions", [])
    status = metadata.get("status", "completed")
    confidence = metadata.get("confidence", 0.9)
    task_description = metadata.get("task_description", "")

    return {
        "agent": {
            "id": agent_id,
            "name": agent_name,
            "type": agent_type,
        },
        "task": {
            "description": task_description,
            "status": status,
            "confidence": confidence,
        },
        "result": raw_result,
        "metadata": {
            "tool_calls_made": tool_calls_made,
            "tools_used": tools_used,
            "tokens_used": {
                "input": tokens.get("input", 0),
                "output": tokens.get("output", 0),
            },
            "cost": {
                "total_usd": cost.get("total_usd", 0.0),
                "breakdown": cost.get("breakdown", {"model": cost.get("total_usd", 0.0), "tools": 0.0}),
            },
            "latency": {
                "total_ms": latency.get("total_ms", 0),
                "llm_ms": latency.get("llm_ms", 0),
                "tools_ms": latency.get("tools_ms", 0),
            },
            "model_used": model,
            "provider": provider,
        },
        "trace": trace,
        "warnings": warnings_list,
        "suggestions": suggestions,
    }
