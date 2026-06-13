import logging
from datetime import datetime, timezone
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

logger = logging.getLogger("successcore.quotas")

TIER_QUOTAS = {
    "FREE": {"api_calls_month": 5000, "agent_runs_month": 100, "storage_mb": 100, "max_users": 50},
    "STARTER": {"api_calls_month": 50000, "agent_runs_month": 500, "storage_mb": 1000, "max_users": 250},
    "PRO": {"api_calls_month": 200000, "agent_runs_month": 2000, "storage_mb": 5000, "max_users": 1000},
    "ENTERPRISE": {"api_calls_month": 999999999, "agent_runs_month": 50000, "storage_mb": 50000, "max_users": 999999},
}

_tenant_usage: Dict[str, dict] = {}


def record_api_call(tenant_id: str):
    if tenant_id not in _tenant_usage:
        _tenant_usage[tenant_id] = {"api_calls": 0, "agent_runs": 0, "month": datetime.now(timezone.utc).strftime("%Y-%m")}
    entry = _tenant_usage[tenant_id]
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    if entry["month"] != current_month:
        entry["api_calls"] = 0
        entry["agent_runs"] = 0
        entry["month"] = current_month
    entry["api_calls"] += 1


def record_agent_run(tenant_id: str):
    if tenant_id not in _tenant_usage:
        _tenant_usage[tenant_id] = {"api_calls": 0, "agent_runs": 0, "month": datetime.now(timezone.utc).strftime("%Y-%m")}
    entry = _tenant_usage[tenant_id]
    entry["agent_runs"] += 1


async def check_quota(tenant_id: str, tier: str, resource: str) -> dict:
    quotas = TIER_QUOTAS.get(tier.upper(), TIER_QUOTAS["FREE"])
    limit = quotas.get(resource, 999999999)
    usage = _tenant_usage.get(tenant_id, {}).get(resource, 0)
    remaining = max(0, limit - usage)
    pct = round(usage / max(limit, 1) * 100, 1) if limit else 0

    return {
        "resource": resource,
        "limit": limit,
        "used": usage,
        "remaining": remaining,
        "usage_pct": pct,
        "blocked": remaining <= 0,
        "tier": tier,
    }


async def get_tenant_quota_status(tenant_id: str, tier: str) -> dict:
    quotas = TIER_QUOTAS.get(tier.upper(), TIER_QUOTAS["FREE"])
    return {
        "tenant_id": tenant_id,
        "tier": tier,
        "quotas": {
            resource: await check_quota(tenant_id, tier, resource)
            for resource in quotas
        },
    }
