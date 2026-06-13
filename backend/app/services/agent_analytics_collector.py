import logging
import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.agent import Agent, AgentExecutionRun

logger = logging.getLogger("successcore.agent_analytics")


class AgentAnalyticsCollector:
    def __init__(self):
        self._buffer: Dict[str, List[Dict[str, Any]]] = {}
        self._last_flush = time.monotonic()

    async def record_run(
        self,
        agent_id: str,
        agent_type: str,
        latency_ms: int,
        tokens_used: int,
        cost_usd: float,
        status: str,
        trigger_source: str,
        tool_calls: int = 0,
    ):
        if agent_id not in self._buffer:
            self._buffer[agent_id] = []
        self._buffer[agent_id].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_type": agent_type,
            "latency_ms": latency_ms,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd,
            "status": status,
            "trigger_source": trigger_source,
            "tool_calls": tool_calls,
        })

    async def get_agent_metrics(
        self,
        agent_id: str,
        db: AsyncSession,
        window_hours: int = 24,
    ) -> Dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        total_runs = 0
        total_success = 0
        total_failed = 0
        total_tokens = 0
        total_cost = 0.0
        total_latency = 0
        by_trigger: Dict[str, int] = {}

        runs = self._buffer.get(agent_id, [])
        for r in runs:
            ts = datetime.fromisoformat(r["timestamp"])
            if ts > cutoff:
                total_runs += 1
                if r["status"] == "completed":
                    total_success += 1
                elif r["status"] == "failed":
                    total_failed += 1
                total_tokens += r["tokens_used"]
                total_cost += r["cost_usd"]
                total_latency += r["latency_ms"]
                trigger = r["trigger_source"]
                by_trigger[trigger] = by_trigger.get(trigger, 0) + 1

        try:
            run_count = await db.execute(
                select(func.count(AgentExecutionRun.id))
                .where(
                    AgentExecutionRun.agent_id == agent_id,
                    AgentExecutionRun.created_at > cutoff,
                )
            )
            db_total = run_count.scalar() or 0

            success_count = await db.execute(
                select(func.count(AgentExecutionRun.id))
                .where(
                    AgentExecutionRun.agent_id == agent_id,
                    AgentExecutionRun.status == "success",
                    AgentExecutionRun.created_at > cutoff,
                )
            )
            db_success = success_count.scalar() or 0

            tokens_res = await db.execute(
                select(func.sum(AgentExecutionRun.token_usage))
                .where(
                    AgentExecutionRun.agent_id == agent_id,
                    AgentExecutionRun.created_at > cutoff,
                )
            )
            db_tokens = tokens_res.scalar() or 0

            cost_res = await db.execute(
                select(func.sum(AgentExecutionRun.cost_usd))
                .where(
                    AgentExecutionRun.agent_id == agent_id,
                    AgentExecutionRun.created_at > cutoff,
                )
            )
            db_cost = cost_res.scalar() or 0.0

            total_runs = max(total_runs, db_total)
            total_success = max(total_success, db_success)
            total_tokens = max(total_tokens, db_tokens)
            total_cost = max(total_cost, float(db_cost))

        except Exception as e:
            logger.debug(f"DB metrics query failed for agent {agent_id}: {e}")

        avg_latency = total_latency / max(total_runs, 1)
        success_rate = total_success / max(total_runs, 1) * 100

        try:
            agent_res = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = agent_res.scalar_one_or_none()
            agent_name = agent.name if agent else "Unknown"
            agent_type = agent.agent_type if agent else "unknown"
        except Exception:
            agent_name = "Unknown"
            agent_type = "unknown"

        return {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "agent_type": agent_type,
            "window_hours": window_hours,
            "total_runs": total_runs,
            "success_count": total_success,
            "failed_count": total_failed,
            "success_rate_pct": round(success_rate, 1),
            "total_tokens_used": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "avg_latency_ms": round(avg_latency, 1),
            "by_trigger_source": by_trigger,
        }

    async def get_all_agents_metrics(
        self,
        db: AsyncSession,
        window_hours: int = 24,
    ) -> List[Dict[str, Any]]:
        agents_res = await db.execute(select(Agent).where(Agent.is_active == True))
        agents = agents_res.scalars().all()

        metrics = []
        for agent in agents:
            metric = await self.get_agent_metrics(agent.id, db, window_hours)
            metrics.append(metric)

        metrics.sort(key=lambda m: m["total_runs"], reverse=True)
        return metrics

    async def get_platform_summary(self, db: AsyncSession) -> Dict[str, Any]:
        all_metrics = await self.get_all_agents_metrics(db)

        total_runs = sum(m["total_runs"] for m in all_metrics)
        total_cost = sum(m["total_cost_usd"] for m in all_metrics)
        total_tokens = sum(m["total_tokens_used"] for m in all_metrics)
        avg_success = (
            sum(m["success_rate_pct"] for m in all_metrics) / max(len(all_metrics), 1)
        )

        by_type: Dict[str, Dict[str, Any]] = {}
        for m in all_metrics:
            atype = m["agent_type"]
            if atype not in by_type:
                by_type[atype] = {"runs": 0, "cost": 0.0, "tokens": 0, "count": 0}
            by_type[atype]["runs"] += m["total_runs"]
            by_type[atype]["cost"] += m["total_cost_usd"]
            by_type[atype]["tokens"] += m["total_tokens_used"]
            by_type[atype]["count"] += 1

        return {
            "total_agents": len(all_metrics),
            "total_runs_24h": total_runs,
            "total_cost_usd_24h": round(total_cost, 6),
            "total_tokens_24h": total_tokens,
            "avg_success_rate_pct": round(avg_success, 1),
            "by_agent_type": by_type,
            "top_agents": all_metrics[:5],
        }

    async def flush(self):
        self._buffer.clear()
        self._last_flush = time.monotonic()


agent_analytics = AgentAnalyticsCollector()
