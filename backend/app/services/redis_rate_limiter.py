import time
import logging
from typing import Optional
from app.core.redis import get_redis

logger = logging.getLogger("successcore.redis_ratelimit")


class RedisTokenBucket:
    def __init__(self, key_prefix: str, rate: float, burst: int, window_seconds: int = 60):
        self.key_prefix = key_prefix
        self.rate = rate
        self.burst = burst
        self.window_seconds = window_seconds

    def _key(self, identifier: str) -> str:
        return f"{self.key_prefix}:{identifier}"

    async def consume(self, identifier: str, amount: int = 1) -> bool:
        try:
            r = await get_redis()
            if r is None:
                return True

            key = self._key(identifier)
            now = time.time()

            lua = """
            local key = KEYS[1]
            local burst = tonumber(ARGV[1])
            local rate = tonumber(ARGV[2])
            local window = tonumber(ARGV[3])
            local now = tonumber(ARGV[4])
            local amount = tonumber(ARGV[5])

            local data = redis.call('HMGET', key, 'tokens', 'last_refill')
            local tokens = tonumber(data[1]) or burst
            local last_refill = tonumber(data[2]) or now

            local elapsed = now - last_refill
            tokens = math.min(burst, tokens + elapsed * rate)

            if tokens >= amount then
                tokens = tokens - amount
                redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
                redis.call('EXPIRE', key, window)
                return 1
            else
                redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
                redis.call('EXPIRE', key, window)
                return 0
            end
            """

            result = await r.eval(
                lua, 1, key,
                str(self.burst), str(self.rate), str(self.window_seconds),
                str(now), str(amount)
            )
            return result == 1
        except Exception as e:
            logger.debug(f"Redis rate limit check failed, allowing: {e}")
            return True

    async def remaining(self, identifier: str) -> int:
        try:
            r = await get_redis()
            if r is None:
                return self.burst
            key = self._key(identifier)
            data = await r.hget(key, "tokens")
            return int(float(data)) if data else self.burst
        except Exception:
            return self.burst


class RedisRateLimiter:
    def __init__(self, prefix: str = "ratelimit"):
        self.prefix = prefix
        self._buckets: dict = {}

    def _get_bucket(self, key: str, rate: float, burst: int) -> RedisTokenBucket:
        cache_key = f"{key}:{rate}:{burst}"
        if cache_key not in self._buckets:
            self._buckets[cache_key] = RedisTokenBucket(
                key_prefix=f"{self.prefix}:{key}",
                rate=rate,
                burst=burst,
            )
        return self._buckets[cache_key]

    async def is_allowed(self, client_key: str, path: str, rate: float, burst: int) -> tuple[bool, int]:
        safe_path = path[:path.find("?")] if "?" in path else path
        identifier = f"{client_key}:{safe_path}"
        bucket = self._get_bucket(client_key, rate, burst)
        allowed = await bucket.consume(identifier)
        remaining = await bucket.remaining(identifier)
        return allowed, remaining


redis_limiter = RedisRateLimiter()
