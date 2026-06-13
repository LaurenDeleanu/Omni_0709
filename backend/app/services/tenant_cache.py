# app/services/tenant_cache.py — Redis-backed tenant configuration cache
import asyncio
import logging
from typing import Optional
from app.core.cache import cache_get, cache_set, cache_delete

logger = logging.getLogger("successcore.tenant_cache")

TENANT_NAMESPACE = "tenant"
TENANT_TTL = 300

# In-memory fallback for when Redis is unavailable
_fallback: dict = {}


async def get_cached_tenant(tenant_id: str) -> Optional[dict]:
    result = await cache_get(TENANT_NAMESPACE, tenant_id)
    if result:
        return result
    cached = _fallback.get(tenant_id)
    if cached:
        return cached
    return None


async def set_cached_tenant(tenant_id: str, data: dict):
    _fallback[tenant_id] = data
    await cache_set(TENANT_NAMESPACE, tenant_id, data, ttl=TENANT_TTL)


async def invalidate_tenant_cache(tenant_id: str):
    _fallback.pop(tenant_id, None)
    await cache_delete(TENANT_NAMESPACE, tenant_id)


async def invalidate_all():
    _fallback.clear()
