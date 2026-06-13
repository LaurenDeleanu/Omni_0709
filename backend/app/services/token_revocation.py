import logging
import json
from typing import Optional
from app.core.redis import get_redis

logger = logging.getLogger("successcore.token_revocation")

TOKEN_BLACKLIST_TTL = 7 * 24 * 3600


async def revoke_token(jti: str) -> bool:
    try:
        r = await get_redis()
        if r is None:
            return False
        await r.setex(f"jwt_blacklist:{jti}", TOKEN_BLACKLIST_TTL, "revoked")
        logger.info(f"Token revoked: jti={jti[:16]}...")
        return True
    except Exception as e:
        logger.error(f"Token revocation failed: {e}")
        return False


async def is_token_revoked(jti: str) -> bool:
    try:
        r = await get_redis()
        if r is None:
            return False
        return await r.exists(f"jwt_blacklist:{jti}") > 0
    except Exception:
        return False
