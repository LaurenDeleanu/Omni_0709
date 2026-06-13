import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from datetime import datetime, timezone

logger = logging.getLogger("successcore.audit_search")


async def search_audit_logs(
    db: AsyncSession,
    query: str = "",
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 100,
) -> dict:
    from app.models.admin import AuditLog

    stmt = select(AuditLog)

    if query:
        stmt = stmt.where(
            or_(AuditLog.action.ilike(f"%{query}%"), AuditLog.details.ilike(f"%{query}%"))
        )
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
    if from_date:
        stmt = stmt.where(AuditLog.created_at >= datetime.fromisoformat(from_date))
    if to_date:
        stmt = stmt.where(AuditLog.created_at <= datetime.fromisoformat(to_date))

    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return {
        "results": [
            {
                "id": l.id,
                "user_id": l.user_id,
                "action": l.action,
                "details": l.details,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ],
        "count": len(logs),
        "filters": {"query": query, "user_id": user_id, "action": action, "from": from_date, "to": to_date},
    }
