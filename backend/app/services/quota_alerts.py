import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.notification import Notification

logger = logging.getLogger("successcore.quota_alerts")

ALERT_THRESHOLD = 0.8


async def check_and_alert_quotas(
    db: AsyncSession,
    tenant_id: str,
    tier: str,
    admin_user_id: str,
) -> List[dict]:
    from app.services.usage_quotas import TIER_QUOTAS, _tenant_usage

    quotas = TIER_QUOTAS.get(tier.upper(), TIER_QUOTAS["FREE"])
    usage = _tenant_usage.get(tenant_id, {})
    if not usage:
        return []

    alerts = []
    now = datetime.now(timezone.utc)
    month_key = now.strftime("%Y-%m")

    for resource, limit in quotas.items():
        if limit >= 999999:
            continue
        used = usage.get(resource, 0)
        pct = used / max(limit, 1)

        if pct >= ALERT_THRESHOLD:
            alert_key = f"quota_{resource}_{month_key}"
            if usage.get(f"_alerted_{resource}") == month_key:
                continue

            import uuid
            notif = Notification(
                id=uuid.uuid4().hex,
                user_id=admin_user_id,
                title=f"Quota Alert: {resource.replace('_', ' ').title()}",
                message=f"You've used {used:,}/{limit:,} ({pct*100:.0f}%) of your monthly {resource.replace('_', ' ')} quota.",
                type="quota_alert",
            )
            db.add(notif)
            usage[f"_alerted_{resource}"] = month_key
            alerts.append({"resource": resource, "used": used, "limit": limit, "pct": round(pct * 100, 1)})

    if alerts:
        await db.flush()
    return alerts
