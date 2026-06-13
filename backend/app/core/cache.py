# app/core/cache.py — Unified Redis caching layer
# Provides cache-aside pattern with TTL, namespacing, and invalidation hooks.
import json
import logging
from typing import Any, Optional

from app.core.redis import get_redis

logger = logging.getLogger("successcore.cache")

DEFAULT_TTL = 300  # 5 minutes


def _key(namespace: str, key: str) -> str:
    return f"cache:{namespace}:{key}"


async def cache_get(namespace: str, key: str) -> Optional[Any]:
    try:
        r = await get_redis()
        raw = await r.get(_key(namespace, key))
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.warning(f"Cache get failed ({namespace}:{key}): {e}")
    return None


async def cache_set(namespace: str, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    try:
        r = await get_redis()
        await r.setex(_key(namespace, key), ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.warning(f"Cache set failed ({namespace}:{key}): {e}")


async def cache_delete(namespace: str, key: str) -> None:
    try:
        r = await get_redis()
        await r.delete(_key(namespace, key))
    except Exception as e:
        logger.warning(f"Cache delete failed ({namespace}:{key}): {e}")


async def cache_invalidate_namespace(namespace: str) -> None:
    try:
        r = await get_redis()
        pattern = f"cache:{namespace}:*"
        cursor = 0
        while True:
            cursor, keys = await r.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await r.delete(*keys)
            if cursor == 0:
                break
    except Exception as e:
        logger.warning(f"Cache namespace invalidation failed ({namespace}): {e}")
