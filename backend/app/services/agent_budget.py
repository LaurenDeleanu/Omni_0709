import logging
from enum import Enum
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import AgentBudgetCap

logger = logging.getLogger("successcore.agent_budget")


class BudgetCheckResult(Enum):
    ALLOWED = "allowed"
    WARNING = "warning"
    BLOCKED = "blocked"
    NO_CAP = "no_cap"


async def _auto_reset(cap: AgentBudgetCap) -> None:
    now = datetime.now(timezone.utc)
    today = now.date()

    if cap.last_reset_daily:
        last_daily_date = cap.last_reset_daily.date()
        if today > last_daily_date:
            cap.daily_spent = 0.0
            cap.last_reset_daily = now
    else:
        cap.last_reset_daily = now

    if cap.last_reset_monthly:
        last_monthly_date = cap.last_reset_monthly.date()
        if today.replace(day=1) > last_monthly_date.replace(day=1):
            cap.monthly_spent = 0.0
            cap.last_reset_monthly = now
    else:
        cap.last_reset_monthly = now


async def check_budget(agent_id: str, estimated_cost: float, db: AsyncSession) -> BudgetCheckResult:
    result = await db.execute(
        select(AgentBudgetCap).where(AgentBudgetCap.agent_id == agent_id)
    )
    cap = result.scalar_one_or_none()
    if not cap:
        return BudgetCheckResult.NO_CAP
    if not cap.is_enforced:
        return BudgetCheckResult.ALLOWED

    await _auto_reset(cap)

    if cap.daily_limit_usd > 0 and (cap.daily_spent + estimated_cost) > cap.daily_limit_usd:
        logger.warning(f"Agent {agent_id} daily budget exceeded: ${cap.daily_spent:.4f} + ${estimated_cost:.4f} > ${cap.daily_limit_usd:.2f}")
        return BudgetCheckResult.BLOCKED

    if cap.monthly_limit_usd > 0 and (cap.monthly_spent + estimated_cost) > cap.monthly_limit_usd:
        logger.warning(f"Agent {agent_id} monthly budget exceeded: ${cap.monthly_spent:.4f} + ${estimated_cost:.4f} > ${cap.monthly_limit_usd:.2f}")
        return BudgetCheckResult.BLOCKED

    daily_ratio = (cap.daily_spent + estimated_cost) / cap.daily_limit_usd if cap.daily_limit_usd > 0 else 0
    monthly_ratio = (cap.monthly_spent + estimated_cost) / cap.monthly_limit_usd if cap.monthly_limit_usd > 0 else 0

    if daily_ratio >= cap.warning_threshold or monthly_ratio >= cap.warning_threshold:
        logger.warning(f"Agent {agent_id} budget warning: daily={daily_ratio:.1%}, monthly={monthly_ratio:.1%}")
        return BudgetCheckResult.WARNING

    return BudgetCheckResult.ALLOWED


async def check_running_budget(agent_id: str, running_cost: float, db: AsyncSession) -> bool:
    """Returns True if the budget is 90% consumed, so the agent should abort."""
    result = await db.execute(
        select(AgentBudgetCap).where(AgentBudgetCap.agent_id == agent_id)
    )
    cap = result.scalar_one_or_none()
    if not cap or not cap.is_enforced:
        return False

    await _auto_reset(cap)

    if cap.daily_limit_usd > 0 and (cap.daily_spent + running_cost) >= (cap.daily_limit_usd * 0.9):
        logger.warning(f"Agent {agent_id} running budget hit 90% of daily limit. Aborting.")
        return True

    if cap.monthly_limit_usd > 0 and (cap.monthly_spent + running_cost) >= (cap.monthly_limit_usd * 0.9):
        logger.warning(f"Agent {agent_id} running budget hit 90% of monthly limit. Aborting.")
        return True

    return False

async def record_cost(agent_id: str, cost_usd: float, db: AsyncSession) -> None:
    result = await db.execute(
        select(AgentBudgetCap).where(AgentBudgetCap.agent_id == agent_id)
    )
    cap = result.scalar_one_or_none()
    if not cap:
        return

    await _auto_reset(cap)
    cap.daily_spent += cost_usd
    cap.monthly_spent += cost_usd
    cap.updated_at = datetime.now(timezone.utc)
    await db.flush()


async def reset_daily_budgets(db: AsyncSession) -> None:
    result = await db.execute(
        select(AgentBudgetCap).where(AgentBudgetCap.is_enforced == True)
    )
    caps = result.scalars().all()
    now = datetime.now(timezone.utc)
    for cap in caps:
        cap.daily_spent = 0.0
        cap.last_reset_daily = now
        cap.updated_at = now
    if caps:
        await db.commit()
        logger.info(f"Daily budgets reset for {len(caps)} agent(s)")
