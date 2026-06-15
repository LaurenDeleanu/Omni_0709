import time
import asyncio
from typing import Dict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


class TokenBucket:
    def __init__(self, rate: int, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def consume(self, amount: int = 1) -> bool:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_refill = now
            if self.tokens >= amount:
                self.tokens -= amount
                return True
            return False


class PerClientRateLimiter(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._buckets: Dict[str, TokenBucket] = {}
        self._bucket_lock = asyncio.Lock()

    def _rate_for_path(self, path: str) -> tuple:
        if "/search" in path:
            return (20, 60)
        if "/agents" in path and ("/run" in path or "/stream" in path):
            return (2, 5)
        if "/omni" in path and "/master" in path:
            return (1, 3)
        if "/signup" in path or "/users/login" in path or "/users/password-reset" in path:
            return (1, 5)  # 1 req/sec, burst 5 for auth routes
        if "/health" in path or "/ready" in path or "/live" in path:
            return (999, 999)
        return (10, 30)

    async def _get_bucket(self, client_key: str, path: str) -> TokenBucket:
        rate, burst = self._rate_for_path(path)
        async with self._bucket_lock:
            bucket_key = f"{client_key}:{path[:path.find('?') if '?' in path else len(path)]}"
            if bucket_key not in self._buckets:
                self._buckets[bucket_key] = TokenBucket(rate=rate, burst=burst)
            return self._buckets[bucket_key]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in ("/health", "/ready", "/live", "/api/v1/users/csrf-token"):
            return await call_next(request)

        client_key = request.headers.get("X-Tenant-ID", request.client.host if request.client else "unknown")
        rate, burst = self._rate_for_path(path)

        try:
            from app.services.redis_rate_limiter import redis_limiter
            allowed, remaining = await redis_limiter.is_allowed(client_key, path, rate, burst)
            if not allowed:
                from app.services.rate_alerts import record_rate_limit_hit
                record_rate_limit_hit(client_key, path)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Retry after a few seconds.",
                    headers={"Retry-After": "5"},
                )
            response = await call_next(request)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response
        except HTTPException:
            raise
        except Exception:
            pass

        bucket = await self._get_bucket(client_key, path)
        if not await bucket.consume():
            from app.services.rate_alerts import record_rate_limit_hit
            record_rate_limit_hit(client_key, path)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Retry after a few seconds.",
                headers={"Retry-After": "5"},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
        return response
