import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

logger = logging.getLogger("successcore.key_rotation")

ROTATION_INTERVAL_DAYS = 90
_rotation_task = None


async def rotate_tenant_keys(db: AsyncSession) -> dict:
    from app.models.tenant import Tenant
    from app.services.field_encryption import generate_tenant_encryption_key

    result = await db.execute(select(Tenant).where(Tenant.is_active == True))
    tenants = result.scalars().all()

    rotated = 0
    errors = 0
    for tenant in tenants:
        try:
            last_rotation = getattr(tenant, 'key_rotated_at', None)
            if last_rotation and (datetime.now(timezone.utc) - last_rotation).days < ROTATION_INTERVAL_DAYS:
                continue

            new_key = generate_tenant_encryption_key(tenant.id)
            old_key = tenant.custom_openai_key or ""
            tenant.custom_openai_key = new_key
            tenant.key_rotated_at = datetime.now(timezone.utc)
            rotated += 1
            logger.info(f"Key rotated for tenant {tenant.name} ({tenant.id[:8]})")
        except Exception as e:
            logger.error(f"Key rotation failed for {tenant.id[:8]}: {e}")
            errors += 1

    if rotated:
        await db.commit()
    return {"rotated": rotated, "errors": errors, "total_checked": len(tenants)}


async def start_key_rotation_scheduler(db_getter):
    global _rotation_task

    async def _loop():
        while True:
            await asyncio.sleep(ROTATION_INTERVAL_DAYS * 86400)
            try:
                async with db_getter() as db:
                    result = await rotate_tenant_keys(db)
                    if result["rotated"]:
                        logger.info(f"Auto-rotated {result['rotated']} tenant keys")
            except Exception as e:
                logger.error(f"Key rotation scheduler error: {e}")

    _rotation_task = asyncio.create_task(_loop())
    logger.info("Key rotation scheduler started (90-day interval)")


def stop_key_rotation():
    global _rotation_task
    if _rotation_task and not _rotation_task.done():
        _rotation_task.cancel()
