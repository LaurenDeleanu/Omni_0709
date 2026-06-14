"""
performance.py — Performance calibration, promotion tracking API.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.api.dependencies import get_tenant_db, get_current_user, require_roles
from app.services.performance_calibration import (
    analyze_team_performance, get_promotion_tracking, calibrate_cycle,
)

router = APIRouter(prefix="/performance", tags=["Performance & Calibration"])


@router.get("/team-analysis")
async def team_performance_analysis(
    manager_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Analyze team performance with forced distribution calibration."""
    tenant_id = current_user.get("tenant_id", "default")
    return await analyze_team_performance(db, tenant_id, manager_id)


@router.get("/promotion-tracking")
async def promotion_readiness(
    manager_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Track promotion readiness across the organization."""
    tenant_id = current_user.get("tenant_id", "default")
    tracking = await get_promotion_tracking(db, tenant_id, manager_id)
    return {"employees": tracking, "count": len(tracking)}


@router.get("/calibrate")
async def run_calibration(
    cycle_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "super_admin", "manager"])),
):
    """Run calibration for a review cycle — normalize across managers."""
    tenant_id = current_user.get("tenant_id", "default")
    return await calibrate_cycle(db, tenant_id, cycle_id)
