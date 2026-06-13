import time
import hashlib
import asyncio
import logging
from typing import Dict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("successcore.api_key_rl")

SCOPE_LIMITS = {
    "read:all": 60,
    "write:all": 30,
    "admin:all": 120,
    "run:agent": 10,
}

_api_key_buckets: Dict[str, dict] = {}
_key_lock = asyncio.Lock()


async def get_key_bucket(key_hash: str) -> dict:
    async with _key_lock:
        now = time.monotonic()
        if key_hash not in _api_key_buckets:
            _api_key_buckets[key_hash] = {"tokens": 60.0, "last_refill": now, "max": 60}
        bucket = _api_key_buckets[key_hash]
        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(bucket["max"], bucket["tokens"] + elapsed * (bucket["max"] / 60.0))
        bucket["last_refill"] = now
        return bucket


class ApiKeyRateLimiter(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("sk-"):
            return await call_next(request)

        api_key = auth.replace("Bearer ", "").replace("sk-", "").strip()
        key_hash = hashlib.sha256(f"sk-{api_key}".encode()).hexdigest()

        from app.services.api_key_manager import validate_api_key
        entry = validate_api_key(f"sk-{api_key}")
        if not entry:
            raise HTTPException(status_code=401, detail="Invalid or revoked API key")

        scopes = entry.get("scopes", ["read:all"])
        limit = max(SCOPE_LIMITS.get(s, 10) for s in scopes)

        bucket = await get_key_bucket(key_hash)
        bucket["max"] = limit

        if bucket["tokens"] < 1:
            raise HTTPException(status_code=429, detail="API key rate limit exceeded", headers={"Retry-After": "5"})

        bucket["tokens"] -= 1
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket["tokens"]))
        response.headers["X-RateLimit-Limit"] = str(limit)
        return response
