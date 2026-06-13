import secrets
import hashlib
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger("successcore.key_rotation")

KEY_ROTATION_DAYS = 90
_rotation_task = None


async def check_and_rotate_keys(db):
    from app.models.api_keys import ApiKey, if_missing_return_empty
    cutoff = datetime.now(timezone.utc) - timedelta(days=KEY_ROTATION_DAYS)
    result = await db.execute(
        select(ApiKey).where(ApiKey.created_at <= cutoff, ApiKey.is_active == True)
    )
    expired = result.scalars().all()
    rotated = 0
    for key in expired:
        key.is_active = False
        new_key = ApiKey(
            id=str(uuid.uuid4().hex) if hasattr(uuid, 'uuid4') else str(secrets.token_hex(16)),
            user_id=key.user_id,
            tenant_id=key.tenant_id,
            key_hash=hashlib.sha256(f"sk-{secrets.token_hex(24)}".encode()).hexdigest(),
            scopes=key.scopes,
            label=f"{key.label or ''} (rotated {datetime.now(timezone.utc).strftime('%Y-%m-%d')})",
        )
        db.add(new_key)
        rotated += 1
    if rotated:
        await db.commit()
        logger.info(f"Auto-rotated {rotated} API keys")
    return rotated


async def start_key_rotation_scheduler(db_getter):
    global _rotation_task
    async def _loop():
        while True:
            await asyncio.sleep(KEY_ROTATION_DAYS * 86400)
            try:
                async with db_getter() as db:
                    await check_and_rotate_keys(db)
            except Exception as e:
                logger.error(f"Key rotation failed: {e}")
    _rotation_task = asyncio.create_task(_loop())
