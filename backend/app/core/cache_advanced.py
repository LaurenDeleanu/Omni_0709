import asyncio
import json
import logging
import time
import zlib
from typing import Any, Callable, Optional

from app.core.redis import get_redis

logger = logging.getLogger("successcore.cache_advanced")

DEFAULT_L1_MAXSIZE = 1000
DEFAULT_L1_TTL = 60
DEFAULT_REDIS_PREFIX = "cache:"
DEFAULT_TTL = 300
COMPRESSION_THRESHOLD = 1024  # bytes — only compress values larger than 1 KiB
STAMPEDE_BETA = 1.0  # XFetch β parameter


class _L1Entry:
    __slots__ = ("value", "expires_at", "tags")

    def __init__(self, value: Any, ttl: int, tags: list[str] | None = None):
        self.value = value
        self.expires_at = time.monotonic() + ttl
        self.tags = tags or []


class TieredCache:
    """Multi-tier cache: L1 (in-process dict with TTL) + L2 (Redis).

    Features:
      - Probabilistic cache-stampede protection (XFetch algorithm)
      - Optional zlib compression for large values
      - Namespace / tag-based invalidation
      - Cache warming via factory callable
      - Hit/miss statistics
    """

    def __init__(
        self,
        l1_maxsize: int = DEFAULT_L1_MAXSIZE,
        l1_ttl: int = DEFAULT_L1_TTL,
        redis_prefix: str = DEFAULT_REDIS_PREFIX,
    ):
        self._l1: dict[str, _L1Entry] = {}
        self._l1_maxsize = l1_maxsize
        self._l1_ttl = l1_ttl
        self._redis_prefix = redis_prefix

        self._hits = 0
        self._misses = 0
        self._l1_hits = 0
        self._l2_hits = 0
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------------

    def _redis_key(self, key: str) -> str:
        return f"{self._redis_prefix}{key}"

    def _compress(self, data: bytes) -> bytes:
        if len(data) < COMPRESSION_THRESHOLD:
            return b"\x00" + data
        return b"\x01" + zlib.compress(data)

    def _decompress(self, raw: bytes) -> bytes:
        flag = raw[0:1]
        payload = raw[1:]
        if flag == b"\x00":
            return payload
        return zlib.decompress(payload)

    def _serialize(self, value: Any) -> str:
        packed = json.dumps(value, default=str, separators=(",", ":")).encode("utf-8")
        compressed = self._compress(packed)
        return compressed.hex()

    def _deserialize(self, raw: str) -> Any:
        compressed = bytes.fromhex(raw)
        payload = self._decompress(compressed)
        return json.loads(payload)

    def _evict_l1(self):
        """Evict expired L1 entries; trim oldest if still over maxsize."""
        now = time.monotonic()
        expired = [k for k, e in self._l1.items() if e.expires_at <= now]
        for k in expired:
            del self._l1[k]

        if len(self._l1) > self._l1_maxsize:
            to_remove = len(self._l1) - self._l1_maxsize
            # remove oldest by expiry time
            sorted_keys = sorted(self._l1.keys(), key=lambda k: self._l1[k].expires_at)
            for k in sorted_keys[:to_remove]:
                del self._l1[k]

    # ------------------------------------------------------------------
    # get / set / delete
    # ------------------------------------------------------------------

    async def get(self, key: str) -> Optional[Any]:
        """Try L1 first, then L2."""
        now = time.monotonic()

        # L1 lookup
        l1_entry = self._l1.get(key)
        if l1_entry is not None and l1_entry.expires_at > now:
            self._hits += 1
            self._l1_hits += 1
            return l1_entry.value

        # L2 lookup
        try:
            r = await get_redis()
            raw = await r.get(self._redis_key(key))
            if raw is not None:
                value = self._deserialize(raw)
                ttl_remaining = await r.ttl(self._redis_key(key))
                l2_ttl = max(int(ttl_remaining), self._l1_ttl) if ttl_remaining > 0 else self._l1_ttl
                self._l1[key] = _L1Entry(value=value, ttl=l2_ttl)
                self._evict_l1()
                self._hits += 1
                self._l2_hits += 1
                return value
        except Exception as e:
            logger.warning(f"L2 get failed ({key}): {e}")

        self._misses += 1
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = DEFAULT_TTL,
        tags: list[str] | None = None,
    ) -> None:
        """Write to L1 + L2 simultaneously."""
        l1_ttl = min(ttl, self._l1_ttl)
        self._l1[key] = _L1Entry(value=value, ttl=l1_ttl, tags=tags)
        self._evict_l1()

        try:
            r = await get_redis()
            serialized = self._serialize(value)
            pipe = r.pipeline()
            pipe.setex(self._redis_key(key), ttl, serialized)
            if tags:
                for tag in tags:
                    pipe.sadd(f"{self._redis_prefix}tag:{tag}", key)
            await pipe.execute()
        except Exception as e:
            logger.warning(f"L2 set failed ({key}): {e}")

    async def delete(self, key: str) -> None:
        """Delete from both tiers."""
        self._l1.pop(key, None)
        try:
            r = await get_redis()
            await r.delete(self._redis_key(key))
        except Exception as e:
            logger.warning(f"L2 delete failed ({key}): {e}")

    # ------------------------------------------------------------------
    # Namespace / tag invalidation
    # ------------------------------------------------------------------

    async def invalidate_namespace(self, namespace: str) -> None:
        """Invalidate all keys with a given namespace tag."""
        deleted_count = 0
        try:
            r = await get_redis()
            tag_key = f"{self._redis_prefix}tag:{namespace}"
            members = await r.smembers(tag_key)
            if members:
                keys = [self._redis_key(m) for m in members]
                await r.delete(*keys)
                await r.delete(tag_key)
                deleted_count = len(members)
        except Exception as e:
            logger.warning(f"Namespace invalidation failed ({namespace}): {e}")

        # L1 cleanup — remove entries whose tags include namespace
        to_remove = [
            k for k, e in self._l1.items() if namespace in (e.tags or [])
        ]
        for k in to_remove:
            del self._l1[k]
            deleted_count += 1

        if deleted_count:
            logger.info(f"Invalidated {deleted_count} entries for namespace '{namespace}'")

    # ------------------------------------------------------------------
    # Cache warming
    # ------------------------------------------------------------------

    async def warm(self, keys: list[str], factory: Callable[..., Any]) -> None:
        """Pre-populate cache from factory(key) for each key."""
        logger.info(f"Warming {len(keys)} cache keys …")
        try:
            tasks = [factory(k) for k in keys if asyncio.iscoroutinefunction(factory)]
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.warning(f"Warm failed for key '{keys[i]}': {result}")
                        continue
                    await self.set(keys[i], result)
            else:
                for k in keys:
                    try:
                        val = factory(k)
                        await self.set(k, val)
                    except Exception as e:
                        logger.warning(f"Warm failed for key '{k}': {e}")
        except Exception as e:
            logger.warning(f"Cache warm batch failed: {e}")

    # ------------------------------------------------------------------
    # get_or_set with cache-stampede protection (XFetch)
    # ------------------------------------------------------------------

    async def get_or_set(
        self,
        key: str,
        factory: Callable[..., Any],
        ttl: int = DEFAULT_TTL,
        stampede_protection: bool = True,
    ) -> Any:
        """Get key, or compute via factory with probabilistic early recomputation.

        When *stampede_protection* is True and the L1 entry is nearing expiry,
        the XFetch algorithm determines whether to proactively recompute.
        This prevents thundering herd under high concurrency.
        """
        import random as _random

        # Try L1 first (fast path)
        entry = self._l1.get(key)
        if entry is not None and entry.expires_at > time.monotonic():
            remaining = entry.expires_at - time.monotonic()
            if stampede_protection and remaining < self._l1_ttl * 0.5:
                gap = max(remaining, 0.001)
                prob = STAMPEDE_BETA * (self._l1_ttl / gap) * _random.random()
                if prob > 1.0:
                    # Early recompute — do in background, return stale value
                    asyncio.ensure_future(self._refresh(key, factory, ttl))
            self._hits += 1
            self._l1_hits += 1
            return entry.value

        # Try L2
        val = await self.get(key)
        if val is not None:
            return val

        # Full miss — compute and store
        async with self._lock:
            # Double-check L1 inside lock (another coroutine may have populated)
            entry = self._l1.get(key)
            if entry is not None and entry.expires_at > time.monotonic():
                return entry.value

            val = await self._compute(factory)
            await self.set(key, val, ttl=ttl)
            return val

    async def _refresh(self, key: str, factory: Callable[..., Any], ttl: int) -> None:
        """Background recompute to refresh a hot key before expiry."""
        try:
            val = await self._compute(factory)
            await self.set(key, val, ttl=ttl)
        except Exception as e:
            logger.warning(f"Background refresh failed for key '{key}': {e}")

    async def _compute(self, factory: Callable[..., Any]) -> Any:
        if asyncio.iscoroutinefunction(factory):
            return await factory()
        return factory()

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0.0
        return {
            "l1_size": len(self._l1),
            "l1_maxsize": self._l1_maxsize,
            "l1_ttl_seconds": self._l1_ttl,
            "hits": self._hits,
            "misses": self._misses,
            "l1_hits": self._l1_hits,
            "l2_hits": self._l2_hits,
            "hit_rate_pct": round(hit_rate, 2),
            "total_requests": total,
        }


# ------------------------------------------------------------------
# Singleton factory
# ------------------------------------------------------------------

_tiered_cache: Optional[TieredCache] = None


async def get_tiered_cache() -> TieredCache:
    global _tiered_cache
    if _tiered_cache is None:
        _tiered_cache = TieredCache()
    return _tiered_cache
