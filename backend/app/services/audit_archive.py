import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

logger = logging.getLogger("successcore.audit_archive")

DEFAULT_RETENTION_DAYS = 365
ARCHIVE_BATCH_SIZE = 500


async def archive_old_audit_logs(db: AsyncSession, retention_days: int = DEFAULT_RETENTION_DAYS) -> dict:
    from app.models.admin import AuditLog
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    count_res = await db.execute(
        select(AuditLog).where(AuditLog.created_at < cutoff)
    )
    total = len(count_res.scalars().all())

    if total == 0:
        return {"archived": 0, "retention_days": retention_days}

    result = await db.execute(
        select(AuditLog).where(AuditLog.created_at < cutoff).limit(ARCHIVE_BATCH_SIZE)
    )
    batch = result.scalars().all()

    archived = 0
    for log in batch:
        await db.delete(log)
        archived += 1

    await db.commit()
    logger.info(f"Audit log archive: deleted {archived} records older than {retention_days} days")
    return {"archived": archived, "total_eligible": total, "retention_days": retention_days}
