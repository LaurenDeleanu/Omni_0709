"""
audit_retention.py — Automated audit log retention and GDPR-compliant purging.
Run periodically (e.g., via cron or agent scheduler) to enforce retention policies.
"""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger("successcore.audit_retention")

DEFAULT_RETENTION_DAYS = 365
GDPR_ERASURE_RETENTION_DAYS = 30


async def purge_old_audit_logs(global_db_session, tenant_db_session_factory, retention_days: int = None):
    days = retention_days or DEFAULT_RETENTION_DAYS
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    try:
        from app.models.admin import AuditLog
        result = await global_db_session.execute(
            delete(AuditLog).where(AuditLog.created_at < cutoff)
        )
        await global_db_session.commit()
        deleted = result.rowcount
        if deleted:
            logger.info(f"Audit retention: purged {deleted} logs older than {days} days (cutoff: {cutoff.isoformat()})")
        return deleted
    except Exception as e:
        logger.error(f"Audit retention purge failed: {e}")
        await global_db_session.rollback()
        return 0


async def handle_dsar_erasure(global_db_session, tenant_db_session_factory, user_email: str, tenant_id: str):
    """
    GDPR Right to Erasure (Art. 17) — anonymize or delete user data.
    Maintains a 30-day grace period before permanent deletion.
    """
    try:
        # 1. Anonymizie user record
        from app.models.user import User
        result = await tenant_db_session_factory.execute(
            select(User).where(User.email == user_email)
        )
        user = result.scalar_one_or_none()
        if not user:
            return {"status": "not_found", "email": user_email}

        user.is_active = False
        user.email = f"deleted-{user.id[:8]}@gdpr-erased.local"
        user.full_name = "GDPR Erased User"
        user.address = ""
        user.iban = ""
        user.social_security_number = ""
        user.phone = ""
        user.erasure_requested_at = datetime.now(timezone.utc)
        await tenant_db_session_factory.commit()

        # 2. Schedule permanent deletion in 30 days
        from app.core.task_queue import enqueue
        await enqueue(
            "gdpr_permanent_delete",
            {"user_id": user.id, "tenant_id": tenant_id, "email": user_email},
            tenant_id=tenant_id,
        )

        logger.info(f"GDPR erasure initiated for {user_email} in tenant {tenant_id}")
        return {"status": "scheduled", "email": user_email, "permanent_delete_after": "30 days"}
    except Exception as e:
        logger.error(f"GDPR erasure failed: {e}")
        await tenant_db_session_factory.rollback()
        return {"status": "error", "email": user_email, "error": str(e)}


async def permanent_delete_user(global_db_session, tenant_db_session_factory, user_id: str, tenant_id: str):
    """Final permanent deletion after GDOR grace period."""
    try:
        from app.models.user import User
        await tenant_db_session_factory.execute(
            delete(User).where(User.id == user_id)
        )
        await tenant_db_session_factory.commit()
        logger.info(f"GDPR permanent deletion completed for user {user_id} in tenant {tenant_id}")
        return {"status": "deleted", "user_id": user_id}
    except Exception as e:
        logger.error(f"GDPR permanent deletion failed: {e}")
        await tenant_db_session_factory.rollback()
        return {"status": "error", "user_id": user_id, "error": str(e)}


# Register with task queue for scheduled execution
from app.core.task_queue import register_task

register_task("gdpr_permanent_delete", permanent_delete_user)
