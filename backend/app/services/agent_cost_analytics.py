import logging
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta
from collections import defaultdict

logger = logging.getLogger("successcore.agent_costs")


async def get_agent_cost_analytics(db: AsyncSession, weeks: int = 12) -> dict:
    from app.models.agent import AgentExecutionRun, Agent, LLMCallAudit

    cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)

    runs_res = await db.execute(
        select(AgentExecutionRun).where(AgentExecutionRun.created_at >= cutoff).order_by(AgentExecutionRun.created_at.desc())
    )
    runs = runs_res.scalars().all()

    by_week: Dict[str, dict] = defaultdict(lambda: {"count": 0, "cost": 0.0, "latency": 0})
    by_agent: Dict[str, dict] = defaultdict(lambda: {"count": 0, "cost": 0.0, "success": 0, "failed": 0})

    for r in runs:
        week_key = r.created_at.strftime("%Y-W%W") if r.created_at else "unknown"
        by_week[week_key]["count"] += 1
        by_week[week_key]["cost"] += r.cost_usd or 0
        by_week[week_key]["latency"] += r.latency_ms or 0

        agent_key = r.agent_id
        by_agent[agent_key]["count"] += 1
        by_agent[agent_key]["cost"] += r.cost_usd or 0
        if r.status == "success":
            by_agent[agent_key]["success"] += 1
        else:
            by_agent[agent_key]["failed"] += 1

    agents_res = await db.execute(select(Agent))
    agents = {a.id: a.name for a in agents_res.scalars().all()}

    weekly_trend = []
    for week, data in sorted(by_week.items()):
        weekly_trend.append({
            "week": week,
            "runs": data["count"],
            "cost_usd": round(data["cost"], 4),
            "avg_latency_ms": round(data["latency"] / max(data["count"], 1), 1),
        })

    agent_breakdown = []
    for aid, data in by_agent.items():
        total = data["count"]
        agent_breakdown.append({
            "agent_id": aid,
            "agent_name": agents.get(aid, aid[:8]),
            "total_runs": total,
            "success_rate": round(data["success"] / max(total, 1) * 100, 1),
            "total_cost": round(data["cost"], 4),
            "avg_cost_per_run": round(data["cost"] / max(total, 1), 6),
        })
    agent_breakdown.sort(key=lambda a: a["total_cost"], reverse=True)

    total_cost = round(sum(d["cost"] for d in by_week.values()), 4)
    total_runs = sum(d["count"] for d in by_week.values())

    # Get model costs using LLMCallAudit
    model_costs = []
    try:
        model_costs_res = await db.execute(
            select(
                LLMCallAudit.model_name,
                func.sum(LLMCallAudit.tokens_used).label("tokens"),
                func.sum(LLMCallAudit.cost_usd).label("cost"),
                func.count(LLMCallAudit.id).label("calls")
            ).where(LLMCallAudit.created_at >= cutoff).group_by(LLMCallAudit.model_name)
        )
        for row in model_costs_res.all():
            model_costs.append({
                "model_name": row[0],
                "total_tokens": int(row[1] or 0),
                "total_cost": float(row[2] or 0.0),
                "total_calls": int(row[3] or 0)
            })
    except Exception as e:
        logger.warning(f"Failed to fetch model costs: {e}")

    return {
        "period": f"{weeks} weeks",
        "total_runs": total_runs,
        "total_cost": total_cost,
        "avg_cost_per_run": round(total_cost / max(total_runs, 1), 6),
        "weekly_trend": weekly_trend,
        "agent_breakdown": agent_breakdown,
        "top_cost_agents": [a for a in agent_breakdown if a["total_cost"] > 0][:5],
        "model_costs": model_costs,
    }


async def get_agent_sla_metrics(db: AsyncSession, agent_id: str, days: int = 30) -> dict:
    from app.models.agent import AgentExecutionRun
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    res = await db.execute(
        select(AgentExecutionRun)
        .where(
            AgentExecutionRun.agent_id == agent_id,
            AgentExecutionRun.created_at >= cutoff
        )
        .order_by(AgentExecutionRun.latency_ms.asc())
    )
    runs = res.scalars().all()
    
    total_runs = len(runs)
    if total_runs == 0:
        return {
            "agent_id": agent_id,
            "period_days": days,
            "total_runs": 0,
            "success_rate": 100.0,
            "p50_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
        }
        
    success_count = sum(1 for r in runs if r.status == "success")
    success_rate = round((success_count / total_runs) * 100.0, 1)
    
    latencies = [r.latency_ms for r in runs if r.latency_ms is not None]
    latencies.sort()
    
    def get_percentile(sorted_list, pct):
        if not sorted_list:
            return 0.0
        idx = int(len(sorted_list) * pct)
        idx = min(idx, len(sorted_list) - 1)
        return float(sorted_list[idx])
        
    return {
        "agent_id": agent_id,
        "period_days": days,
        "total_runs": total_runs,
        "success_rate": success_rate,
        "p50_latency_ms": get_percentile(latencies, 0.50),
        "p95_latency_ms": get_percentile(latencies, 0.95),
        "p99_latency_ms": get_percentile(latencies, 0.99),
    }
