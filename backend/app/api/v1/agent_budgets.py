from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from pydantic import BaseModel

from app.api.dependencies import get_tenant_db, require_roles, get_current_user
from app.models.agent import AgentBudgetCap
from app.services.agent_budget import check_budget, BudgetCheckResult
import uuid

router = APIRouter()


class BudgetCapCreate(BaseModel):
    agent_id: str
    daily_limit_usd: float = 10.0
    monthly_limit_usd: float = 200.0
    warning_threshold: float = 0.8
    is_enforced: bool = True


@router.get("/")
async def list_budgets(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(AgentBudgetCap).order_by(AgentBudgetCap.updated_at.desc())
    )
    caps = result.scalars().all()
    return [
        {
            "id": c.id,
            "agent_id": c.agent_id,
            "daily_limit_usd": c.daily_limit_usd,
            "monthly_limit_usd": c.monthly_limit_usd,
            "warning_threshold": c.warning_threshold,
            "is_enforced": c.is_enforced,
            "daily_spent": c.daily_spent,
            "monthly_spent": c.monthly_spent,
            "last_reset_daily": c.last_reset_daily.isoformat() if c.last_reset_daily else None,
            "last_reset_monthly": c.last_reset_monthly.isoformat() if c.last_reset_monthly else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in caps
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_or_update_budget(
    body: BudgetCapCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(AgentBudgetCap).where(AgentBudgetCap.agent_id == body.agent_id)
    )
    cap = result.scalar_one_or_none()

    if cap:
        cap.daily_limit_usd = body.daily_limit_usd
        cap.monthly_limit_usd = body.monthly_limit_usd
        cap.warning_threshold = body.warning_threshold
        cap.is_enforced = body.is_enforced
        cap.updated_at = datetime.now(timezone.utc)
    else:
        cap = AgentBudgetCap(
            id=uuid.uuid4().hex,
            agent_id=body.agent_id,
            daily_limit_usd=body.daily_limit_usd,
            monthly_limit_usd=body.monthly_limit_usd,
            warning_threshold=body.warning_threshold,
            is_enforced=body.is_enforced,
        )
        db.add(cap)

    await db.commit()
    await db.refresh(cap)
    return {
        "id": cap.id,
        "agent_id": cap.agent_id,
        "daily_limit_usd": cap.daily_limit_usd,
        "monthly_limit_usd": cap.monthly_limit_usd,
        "is_enforced": cap.is_enforced,
    }


@router.get("/{agent_id}")
async def get_budget_status(
    agent_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(AgentBudgetCap).where(AgentBudgetCap.agent_id == agent_id)
    )
    cap = result.scalar_one_or_none()
    if not cap:
        raise HTTPException(status_code=404, detail="Budget cap not found for this agent")

    budget_check = await check_budget(agent_id, 0.0, db)

    daily_pct = (cap.daily_spent / cap.daily_limit_usd * 100) if cap.daily_limit_usd > 0 else 0
    monthly_pct = (cap.monthly_spent / cap.monthly_limit_usd * 100) if cap.monthly_limit_usd > 0 else 0

    return {
        "agent_id": cap.agent_id,
        "daily_limit_usd": cap.daily_limit_usd,
        "monthly_limit_usd": cap.monthly_limit_usd,
        "warning_threshold": cap.warning_threshold,
        "is_enforced": cap.is_enforced,
        "daily_spent": cap.daily_spent,
        "monthly_spent": cap.monthly_spent,
        "daily_pct": round(daily_pct, 2),
        "monthly_pct": round(monthly_pct, 2),
        "status": budget_check.value,
        "last_reset_daily": cap.last_reset_daily.isoformat() if cap.last_reset_daily else None,
        "last_reset_monthly": cap.last_reset_monthly.isoformat() if cap.last_reset_monthly else None,
    }
