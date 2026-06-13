import logging
from typing import Callable
from fastapi import Request, HTTPException, status
from app.core.redis import get_redis

logger = logging.getLogger("successcore.ratelimit")

def RateLimiter(limit: str) -> Callable:
    """
    Dependency that enforces rate limiting per endpoint per IP or user.
    Example: Depends(RateLimiter("10/minute"))
    """
    try:
        req_limit, time_unit = limit.split("/")
        req_limit = int(req_limit)
        time_seconds = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400
        }.get(time_unit.lower(), 60)
    except ValueError:
        raise ValueError("Invalid rate limit format. Use '10/minute'")

    async def _rate_limit_dependency(request: Request):
        # Prefer user ID if authenticated, else IP
        user_id = getattr(request.state, "user", {}).get("sub")
        client_ip = request.client.host if request.client else "unknown"
        identifier = user_id or client_ip
        
        endpoint = request.url.path
        
        redis_client = await get_redis()
        key = f"rate_limit:{endpoint}:{identifier}"
        
        try:
            current_count = await redis_client.get(key)
            if current_count and int(current_count) >= req_limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Try again later."
                )
            
            pipe = redis_client.pipeline()
            pipe.incr(key)
            if not current_count:
                pipe.expire(key, time_seconds)
            await pipe.execute()
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            logger.warning(f"RateLimiter Redis error: {e}")
            # If Redis fails, allow the request rather than failing closed
            pass
            
    return _rate_limit_dependency
