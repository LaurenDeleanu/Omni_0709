import time
import asyncio
import logging
from typing import Dict
from collections import defaultdict

logger = logging.getLogger("successcore.oauth_rl")

TIER_LIMITS = {
    "default": 60,
    "premium": 600,
    "enterprise": 6000,
}

_client_buckets: Dict[str, dict] = {}
_bucket_lock = asyncio.Lock()


async def check_oauth_rate_limit(client_id: str, tier: str = "default") -> bool:
    limit = TIER_LIMITS.get(tier, TIER_LIMITS["default"])
    async with _bucket_lock:
        now = time.monotonic()
        if client_id not in _client_buckets:
            _client_buckets[client_id] = {"tokens": float(limit), "last_refill": now}
        bucket = _client_buckets[client_id]
        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(limit, bucket["tokens"] + elapsed * (limit / 60.0))
        bucket["last_refill"] = now
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        return False


def get_oauth_rate_limit_status(client_id: str, tier: str = "default") -> dict:
    limit = TIER_LIMITS.get(tier, TIER_LIMITS["default"])
    bucket = _client_buckets.get(client_id, {"tokens": float(limit)})
    return {"client_id": client_id, "tier": tier, "limit_per_minute": limit, "remaining": int(bucket["tokens"])}
