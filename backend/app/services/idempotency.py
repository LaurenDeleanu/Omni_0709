import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("successcore.idempotency")


async def check_idempotency(agent_id: str, user_id: str, idempotency_key: str, db: AsyncSession) -> dict | None:
    try:
        from app.core.redis import get_redis
        r = await get_redis()
        key = f"idem:{agent_id}:{user_id}:{idempotency_key}"
        cached = await r.get(key)
        if cached:
            logger.debug(f"Idempotency cache hit for key={idempotency_key}")
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Idempotency check failed (non-fatal): {e}")
    return None


async def store_idempotency(agent_id: str, user_id: str, idempotency_key: str, result: dict, ttl: int = 86400, db: AsyncSession = None) -> None:
    try:
        from app.core.redis import get_redis
        r = await get_redis()
        key = f"idem:{agent_id}:{user_id}:{idempotency_key}"
        await r.set(key, json.dumps(result, default=str), ex=ttl)
    except Exception as e:
        logger.warning(f"Idempotency store failed (non-fatal): {e}")
