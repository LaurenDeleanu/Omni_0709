# app/core/redis.py — Shared Redis client singleton
# Used by cache.py and task_queue.py. Single connection pool.
import logging
from typing import Optional
import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger("successcore.redis")

_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            settings.REDIS_URI,
            decode_responses=True,
            protocol=2,  # RESP2 for older Redis
            socket_timeout=5,
            socket_connect_timeout=5,
        )
    return _client
