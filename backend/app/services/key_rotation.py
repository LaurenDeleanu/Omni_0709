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
    """
    Desactiva las claves API (OAuthClient del Developer Portal) con más de
    KEY_ROTATION_DAYS días de antigüedad.

    Nota: el secreto en texto plano solo se muestra al crear la clave, por lo
    que no es posible generar automáticamente una clave de reemplazo utilizable
    desde un proceso en segundo plano. En su lugar, se desactiva la clave
    caducada y se avisa para que un administrador emita una nueva desde el
    Developer Portal.
    """
    from app.models.oauth import OAuthClient
    cutoff = datetime.now(timezone.utc) - timedelta(days=KEY_ROTATION_DAYS)
    result = await db.execute(
        select(OAuthClient).where(OAuthClient.created_at <= cutoff, OAuthClient.is_active == True)
    )
    expired = result.scalars().all()
    rotated = 0
    for key in expired:
        key.is_active = False
        rotated += 1
        logger.warning(
            f"API key '{key.name}' ({key.id}) del tenant {key.tenant_id} desactivada "
            f"por antigüedad (> {KEY_ROTATION_DAYS} días). "
            "Emitir una nueva clave desde el Developer Portal."
        )
    if rotated:
        await db.commit()
        logger.info(f"Auto-rotated (deactivated) {rotated} expired API keys")
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
