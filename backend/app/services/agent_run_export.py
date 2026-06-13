import io
import csv
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger("successcore.agent_export")


async def export_agent_runs_csv(db: AsyncSession, agent_id: Optional[str] = None, limit: int = 1000) -> str:
    from app.models.agent import AgentExecutionRun

    stmt = select(AgentExecutionRun).order_by(AgentExecutionRun.created_at.desc()).limit(limit)
    if agent_id:
        stmt = stmt.where(AgentExecutionRun.agent_id == agent_id)

    result = await db.execute(stmt)
    runs = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "agent_id", "trigger_source", "status", "loop_count", "token_usage", "cost_usd", "latency_ms", "created_at"])

    for r in runs:
        writer.writerow([r.id, r.agent_id, r.trigger_source, r.status, r.loop_count, r.token_usage, r.cost_usd, r.latency_ms, r.created_at.isoformat() if r.created_at else ""])

    return output.getvalue()
