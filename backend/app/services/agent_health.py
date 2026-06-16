import logging
import asyncio
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import case, func as safunc
from sqlalchemy import select, func
from datetime import datetime, timezone
import uuid

from app.models.agent import Agent, AgentHealthRecord, AgentExecutionRun

logger = logging.getLogger("successcore.agent_health")

DEGRADED_LATENCY_THRESHOLD_MS = 10000
DEGRADED_SUCCESS_RATE_THRESHOLD = 0.90
HEALTH_CHECK_INTERVAL_SECONDS = 300
HEALTH_PING_TIMEOUT_SECONDS = 8.0
HEALTH_FREE_MODEL_LATENCY_MS = 6000


async def check_agent_health(agent_id: str, db: AsyncSession) -> Dict[str, Any]:
    import time as _time

    agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_result.scalar_one_or_none()
    if not agent:
        return {"status": "not_found", "agent_id": agent_id}

    start_ts = _time.monotonic()
    success = False
    error_message = None

    run_stmt = (
        select(
            func.count(AgentExecutionRun.id).label("total"),
            safunc.sum(
                case(
                    (AgentExecutionRun.status == "success", 1), else_=0
                )
            ).label("successes"),
            safunc.sum(
                case(
                    (AgentExecutionRun.status == "failed", 1), else_=0
                )
            ).label("failures"),
        )
        .where(
            AgentExecutionRun.agent_id == agent_id,
            AgentExecutionRun.created_at >= func.now() - func.make_interval(0, 0, 0, 0, 1, 0, 0),
        )
    )
    run_result = await db.execute(run_stmt)
    row = run_result.one_or_none()

    total = int(row.total or 0)
    successes = int(row.successes or 0)
    fail_count = int(row.failures or 0)
    success_rate = round(successes / total, 4) if total > 0 else 1.0

    consecutive_failures = 0
    recent_runs_result = await db.execute(
        select(AgentExecutionRun.status)
        .where(AgentExecutionRun.agent_id == agent_id)
        .order_by(AgentExecutionRun.created_at.desc())
        .limit(10)
    )
    for status in recent_runs_result.scalars().all():
        if status == "failed":
            consecutive_failures += 1
        else:
            break

    # Passive health check: no active LLM pings to save API quota
    if consecutive_failures >= 3:
        success = False
        error_message = f"{consecutive_failures} consecutive execution failures"
    elif success_rate < DEGRADED_SUCCESS_RATE_THRESHOLD and total >= 5:
        success = False
        error_message = f"Success rate dropped to {success_rate*100}%"
    else:
        success = True
        error_message = None

    response_time_ms = int((_time.monotonic() - start_ts) * 1000)

    is_free_model = ":free" in (agent.ai_model or "")
    latency_threshold = HEALTH_FREE_MODEL_LATENCY_MS if is_free_model else DEGRADED_LATENCY_THRESHOLD_MS

    status = "healthy"
    if not success:
        status = "unhealthy"
    elif consecutive_failures >= 3:
        status = "degraded"
    elif success_rate < DEGRADED_SUCCESS_RATE_THRESHOLD:
        status = "degraded"
    elif response_time_ms > latency_threshold:
        status = "degraded"

    health_record = AgentHealthRecord(
        id=uuid.uuid4().hex,
        agent_id=agent_id,
        status=status,
        response_time_ms=response_time_ms,
        error_message=error_message,
        tenant_id=agent.tenant_id,
    )
    db.add(health_record)
    await db.flush()

    if status != "healthy":
        logger.warning(
            f"Agent {agent.name} ({agent_id}) health: {status} | "
            f"latency={response_time_ms}ms | fails={fail_count} | "
            f"consecutive_fails={consecutive_failures}"
        )

    health_data = {
        "agent_id": agent_id,
        "agent_name": agent.name,
        "status": status,
        "response_time_ms": response_time_ms,
        "success": success,
        "error_message": error_message,
        "recent_success_rate": success_rate,
        "consecutive_failures": consecutive_failures,
        "is_circuit_breaker_open": consecutive_failures >= 5,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total_runs_1h": total,
        "success_count_1h": successes,
        "fail_count_1h": fail_count,
    }

    await set_agent_health_cache(agent_id, {
        "healthy": status == "healthy",
        "latency_ms": response_time_ms,
        "consecutive_failures": consecutive_failures,
        "status": status,
    })

    return health_data


async def monitor_all_agents(db_session_factory):
    from app.core.database import AsyncSessionGlobal

    logger.info("Agent health monitor started (interval=%ds)", HEALTH_CHECK_INTERVAL_SECONDS)

    while True:
        try:
            async with db_session_factory() as db:
                result = await db.execute(select(Agent).where(Agent.is_active == True))
                agents = list(result.scalars().all())

                for agent in agents:
                    health = await check_agent_health(agent.id, db)
                    status = health.get("status", "unknown")
                    if status in ("degraded", "unhealthy"):
                        try:
                            logger.warning(
                                f"Health alert: Agent {agent.name} is {status} — "
                                f"latency={health.get('response_time_ms')}ms, "
                                f"consecutive_failures={health.get('consecutive_failures', 0)}"
                            )
                        except Exception:
                            pass

                    if health.get("consecutive_failures", 0) >= 5:
                        logger.error(
                            f"Circuit breaker threshold reached for agent {agent.name} ({agent.id})"
                        )
            await db.commit()
        except Exception as e:
            logger.error(f"Health monitor cycle failed: {e}")

        await asyncio.sleep(HEALTH_CHECK_INTERVAL_SECONDS)


_health_cache: Dict[str, Dict[str, Any]] = {}
_health_cache_lock = asyncio.Lock()


async def get_agent_health_status(agent_id: str) -> Dict[str, Any]:
    async with _health_cache_lock:
        return _health_cache.get(agent_id, {"healthy": True, "latency_ms": 0, "consecutive_failures": 0})


async def set_agent_health_cache(agent_id: str, data: Dict[str, Any]):
    async with _health_cache_lock:
        _health_cache[agent_id] = data





async def get_all_agents_health_summary(db: AsyncSession) -> Dict[str, Any]:
    result = await db.execute(select(Agent).where(Agent.is_active == True))
    agents = result.scalars().all()

    healthy = 0
    degraded = 0
    unhealthy = 0
    total = len(agents)
    details = []

    for agent in agents:
        agent_id = agent.id
        health = await get_agent_health_status(agent_id)
        status = health.get("status", "healthy")
        if status == "healthy":
            healthy += 1
        elif status == "degraded":
            degraded += 1
        else:
            unhealthy += 1
        details.append({
            "agent_id": agent.id,
            "name": agent.name,
            "type": agent.agent_type,
            "model": agent.ai_model,
            "healthy": health.get("healthy", True),
            "latency_ms": health.get("latency_ms", 0),
            "status": status,
        })

    return {
        "total_agents": total,
        "healthy": healthy,
        "degraded": degraded,
        "unhealthy": unhealthy,
        "health_ratio": round(healthy / max(total, 1), 2),
        "agents": details,
    }
