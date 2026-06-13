import logging
import hashlib
import json
import time
from typing import Optional, Any
from app.core.cache import cache_get, cache_set

logger = logging.getLogger("successcore.api_cache")

API_CACHE_TTL = 300
API_CACHE_PREFIX = "api_response"


def _cache_key(method: str, path: str, tenant_id: str, query_params: str = "") -> str:
    raw = f"{method}:{path}:{tenant_id}:{query_params}"
    return f"{API_CACHE_PREFIX}:{hashlib.sha256(raw.encode()).hexdigest()[:24]}"


async def get_cached_response(
    method: str, path: str, tenant_id: str, query_params: str = ""
) -> Optional[dict]:
    key = _cache_key(method, path, tenant_id, query_params)
    cached = await cache_get(API_CACHE_PREFIX, key)
    if cached:
        logger.debug(f"Cache HIT: {method} {path}")
        return cached
    logger.debug(f"Cache MISS: {method} {path}")
    return None


async def set_cached_response(
    method: str, path: str, tenant_id: str, response: Any, query_params: str = "",
    ttl: int = API_CACHE_TTL,
):
    key = _cache_key(method, path, tenant_id, query_params)
    await cache_set(API_CACHE_PREFIX, key, response, ttl=ttl)


async def invalidate_cache_for_resource(resource_prefix: str, tenant_id: str):
    try:
        from app.core.redis import get_redis
        r = await get_redis()
        if r is None:
            return
        pattern = f"{API_CACHE_PREFIX}:*"
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = await r.scan(cursor=cursor, match=pattern, count=100)
            for key in keys:
                if resource_prefix in key:
                    await r.delete(key)
                    deleted += 1
            if cursor == 0:
                break
        if deleted:
            logger.debug(f"Invalidated {deleted} cache entries for resource: {resource_prefix}")
    except Exception as e:
        logger.debug(f"Cache invalidation failed: {e}")


CACHEABLE_PATHS = {
    "/api/v1/employees": 300,
    "/api/v1/reports": 600,
    "/api/v1/metadata": 3600,
    "/api/v1/training/courses": 600,
    "/api/v1/agents/specialists": 3600,
    "/api/v1/agents/model-catalog": 3600,
    "/api/v1/agents/specialists": 3600,
    "/api/v1/org-chart": 300,
    "/api/v1/calendar": 120,
}


def should_cache(path: str, method: str) -> tuple[bool, int]:
    if method != "GET":
        return False, 0
    for cache_path, ttl in CACHEABLE_PATHS.items():
        if path.startswith(cache_path):
            return True, ttl
    return False, 0
