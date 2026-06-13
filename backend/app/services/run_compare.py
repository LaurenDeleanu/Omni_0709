import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

logger = logging.getLogger("successcore.run_compare")


async def compare_agent_runs(db: AsyncSession, run_id_a: str, run_id_b: str) -> dict:
    from app.models.agent import AgentExecutionRun

    result_a = await db.execute(select(AgentExecutionRun).where(AgentExecutionRun.id == run_id_a))
    run_a = result_a.scalar_one_or_none()
    result_b = await db.execute(select(AgentExecutionRun).where(AgentExecutionRun.id == run_id_b))
    run_b = result_b.scalar_one_or_none()

    if not run_a or not run_b:
        raise ValueError("One or both runs not found")

    import json

    trace_a = json.loads(run_a.execution_trace) if run_a.execution_trace else []
    trace_b = json.loads(run_b.execution_trace) if run_b.execution_trace else []

    return {
        "run_a": {
            "id": run_a.id, "status": run_a.status, "latency_ms": run_a.latency_ms,
            "cost_usd": run_a.cost_usd, "token_usage": run_a.token_usage,
            "steps": len(trace_a), "created_at": run_a.created_at.isoformat() if run_a.created_at else None,
        },
        "run_b": {
            "id": run_b.id, "status": run_b.status, "latency_ms": run_b.latency_ms,
            "cost_usd": run_b.cost_usd, "token_usage": run_b.token_usage,
            "steps": len(trace_b), "created_at": run_b.created_at.isoformat() if run_b.created_at else None,
        },
        "comparison": {
            "latency_diff_ms": (run_a.latency_ms or 0) - (run_b.latency_ms or 0),
            "cost_diff_usd": round((run_a.cost_usd or 0) - (run_b.cost_usd or 0), 6),
            "token_diff": (run_a.token_usage or 0) - (run_b.token_usage or 0),
            "steps_diff": len(trace_a) - len(trace_b),
        },
        "trace_a": trace_a,
        "trace_b": trace_b,
    }
