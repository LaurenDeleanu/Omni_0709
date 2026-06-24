"""
usage_billing.py — Usage-based billing and AI token consumption tracking.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

logger = logging.getLogger("successcore.usage_billing")

TOKEN_PRICES = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "claude-3": {"input": 0.003, "output": 0.015},
    "gemini-1.5": {"input": 0.00125, "output": 0.005},
    "default": {"input": 0.001, "output": 0.005},
}

STORE_PRICES = {
    "pro_agent": 9.99,
    "enterprise_agent": 49.99,
    "custom_integration": 199.99,
}


async def get_tenant_usage_summary(
    db: AsyncSession,
    tenant_id: str,
    days: int = 30,
) -> dict:
    """Get aggregated AI token usage for a tenant."""
    from app.models.agent import AgentExecutionRun

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(AgentExecutionRun).where(
            AgentExecutionRun.created_at >= cutoff,
        )
    )
    runs = result.scalars().all()

    total_tokens = 0
    total_cost = 0.0
    by_model: dict[str, dict] = {}
    by_agent: dict[str, dict] = {}
    daily: dict[str, dict] = {}

    for run in runs:
        tokens =         getattr(run, "token_usage", 0) or 0
        model = getattr(run, "model", "default") or "default"
        agent_id = getattr(run, "agent_id", "unknown")
        day_key = run.created_at.strftime("%Y-%m-%d") if run.created_at else None

        prices = TOKEN_PRICES.get(model, TOKEN_PRICES["default"])
        cost = (tokens / 1000) * prices["output"]

        total_tokens += tokens
        total_cost += cost

        by_model.setdefault(model, {"tokens": 0, "cost": 0.0, "runs": 0})
        by_model[model]["tokens"] += tokens
        by_model[model]["cost"] += cost
        by_model[model]["runs"] += 1

        by_agent.setdefault(agent_id, {"tokens": 0, "cost": 0.0, "runs": 0})
        by_agent[agent_id]["tokens"] += tokens
        by_agent[agent_id]["cost"] += cost
        by_agent[agent_id]["runs"] += 1

        if day_key:
            daily.setdefault(day_key, {"tokens": 0, "cost": 0})
            daily[day_key]["tokens"] += tokens
            daily[day_key]["cost"] += cost

    return {
        "period_days": days,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "total_runs": len(runs),
        "by_model": {m: {"tokens": d["tokens"], "cost": round(d["cost"], 4), "runs": d["runs"]} for m, d in by_model.items()},
        "by_agent": {a: {"tokens": d["tokens"], "cost": round(d["cost"], 4), "runs": d["runs"]} for a, d in by_agent.items()},
        "daily": {day: {"tokens": d["tokens"], "cost": round(d["cost"], 4)} for day, d in sorted(daily.items())},
    }


async def generate_monthly_bill(
    db: AsyncSession,
    tenant_id: str,
    month: Optional[str] = None,
) -> dict:
    """Generate a monthly usage bill for a tenant."""
    if not month:
        month = datetime.now(timezone.utc).strftime("%Y-%m")

    year, mon = int(month[:4]), int(month[5:7])
    period_start = datetime(year, mon, 1, tzinfo=timezone.utc)
    if mon == 12:
        period_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        period_end = datetime(year, mon + 1, 1, tzinfo=timezone.utc)

    from app.models.agent import AgentExecutionRun
    result = await db.execute(
        select(AgentExecutionRun).where(
            AgentExecutionRun.created_at >= period_start,
            AgentExecutionRun.created_at < period_end,
        )
    )
    runs = result.scalars().all()

    line_items = []
    total = 0.0

    # AI usage costs
    by_model: dict[str, dict] = {}
    for run in runs:
        tokens =         getattr(run, "token_usage", 0) or 0
        model = getattr(run, "model", "default") or "default"
        prices = TOKEN_PRICES.get(model, TOKEN_PRICES["default"])
        cost = round((tokens / 1000) * prices["output"], 4)
        by_model.setdefault(model, {"tokens": 0, "cost": 0.0})
        by_model[model]["tokens"] += tokens
        by_model[model]["cost"] += cost

    for model, data in by_model.items():
        cost = round(data["cost"], 2)
        line_items.append({
            "description": f"AI Usage — {model}",
            "tokens": data["tokens"],
            "unit": "per 1K tokens",
            "amount": cost,
        })
        total += cost

    # Base plan fee
    from app.models.tenant import Tenant
    from app.core.database import AsyncSessionGlobal
    async with AsyncSessionGlobal() as global_db:
        tenant_result = await global_db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = tenant_result.scalar_one_or_none()
    tier = tenant.tier if tenant else "FREE"
    base_prices = {"FREE": 0, "PRO": 99.00, "ENTERPRISE": 499.00}
    base_fee = base_prices.get(tier, 0)
    line_items.append({"description": f"Base Plan — {tier}", "tokens": 0, "unit": "flat/month", "amount": base_fee})
    total += base_fee

    return {
        "tenant_id": tenant_id,
        "period": month,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "base_plan": tier,
        "base_fee": base_fee,
        "usage_cost": round(total - base_fee, 2),
        "total_due": round(total, 2),
        "line_items": line_items,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
