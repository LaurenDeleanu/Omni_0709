import logging
import time
import asyncio
from typing import Dict, Any

logger = logging.getLogger("successcore.synthetic_monitor")

_health_check_history: list = []
_max_history = 100


async def probe_database() -> Dict[str, Any]:
    start = time.monotonic()
    try:
        from app.core.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await asyncio.wait_for(conn.execute(text("SELECT 1")), timeout=3.0)
        return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 1)}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200], "latency_ms": round((time.monotonic() - start) * 1000, 1)}


async def probe_redis() -> Dict[str, Any]:
    start = time.monotonic()
    try:
        from app.core.redis import get_redis
        r = await get_redis()
        if r is None:
            return {"status": "unavailable", "latency_ms": 0}
        await asyncio.wait_for(r.ping(), timeout=2.0)
        return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 1)}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200], "latency_ms": round((time.monotonic() - start) * 1000, 1)}


async def probe_llm_providers() -> Dict[str, Any]:
    start = time.monotonic()
    providers = {}
    from app.core.config import settings
    if settings.OPENAI_API_KEY:
        providers["openai"] = "configured"
    if settings.GEMINI_API_KEY:
        providers["gemini"] = "configured"
    return {"status": "ok" if providers else "unavailable", "configured_providers": providers, "latency_ms": round((time.monotonic() - start) * 1000, 1)}


async def run_synthetic_check() -> Dict[str, Any]:
    now = time.monotonic()
    db = await probe_database()
    redis = await probe_redis()
    llm = await probe_llm_providers()

    overall = "healthy" if db["status"] == "ok" else "degraded"

    result = {
        "timestamp": time.time(),
        "overall": overall,
        "components": {"database": db, "redis": redis, "llm_providers": llm},
        "total_latency_ms": round((time.monotonic() - now) * 1000, 1),
    }

    _health_check_history.append(result)
    if len(_health_check_history) > _max_history:
        _health_check_history.pop(0)

    if overall != "healthy":
        logger.warning(f"SYNTHETIC_MONITOR: {overall} | db={db['status']} redis={redis['status']}")

    return result


def get_synthetic_history(limit: int = 20) -> list:
    return _health_check_history[-limit:]


async def start_synthetic_monitor(interval_seconds: int = 60):
    async def _loop():
        while True:
            await asyncio.sleep(interval_seconds)
            await run_synthetic_check()

    asyncio.create_task(_loop())
    logger.info(f"Synthetic monitor started (interval={interval_seconds}s)")
