import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone

logger = logging.getLogger("successcore.crosstenant")


async def get_platform_analytics(global_db: AsyncSession) -> dict:
    from app.models.tenant import Tenant

    tenant_res = await global_db.execute(select(Tenant))
    tenants = tenant_res.scalars().all()

    total_tenants = len(tenants)
    active_tenants = sum(1 for t in tenants if t.is_active)
    by_tier = {}
    for t in tenants:
        tier = t.tier or "FREE"
        by_tier[tier] = by_tier.get(tier, 0) + 1

    thirty_days_ago = datetime.now(timezone.utc)
    new_this_month = sum(1 for t in tenants if t.created_at and t.created_at >= thirty_days_ago.replace(day=1))

    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "inactive_tenants": total_tenants - active_tenants,
        "by_tier": by_tier,
        "new_tenants_this_month": new_this_month,
        "tenants": [
            {
                "id": t.id,
                "name": t.name,
                "schema": t.schema_name,
                "tier": t.tier,
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tenants
        ],
    }
