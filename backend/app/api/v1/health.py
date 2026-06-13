"""
Health check endpoint for load balancers, orchestrators, and monitoring systems.
Returns component-level availability for DB, Redis, and LLM providers.
"""

from fastapi import APIRouter
import logging
import time

logger = logging.getLogger("successcore.health")

router = APIRouter()


async def _check_database() -> dict:
    """Verify PostgreSQL connectivity."""
    try:
        from app.core.database import AsyncSessionGlobal
        start = time.monotonic()
        async with AsyncSessionGlobal() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        return {"status": "ok", "latency_ms": latency_ms}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "degraded", "error": str(e)[:200]}


async def _check_redis() -> dict:
    """Verify Redis connectivity."""
    try:
        from app.core.redis import get_redis
        start = time.monotonic()
        r = await get_redis()
        if r is None:
            return {"status": "unavailable", "error": "Redis not configured"}
        await r.ping()
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        return {"status": "ok", "latency_ms": latency_ms}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {"status": "degraded", "error": str(e)[:200]}


async def _check_llm_providers() -> dict:
    """Return circuit-breaker health for each LLM provider."""
    try:
        from app.services.model_fallback import get_provider_health
        tracker = get_provider_health()
        stats = await tracker.get_all_stats()
        return {
            "status": "ok",
            "providers": {s["provider"]: {"healthy": s["healthy"], "circuit_open": s["circuit_open"]} for s in stats},
        }
    except Exception as e:
        return {"status": "unknown", "error": str(e)[:200]}


@router.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint.

    Returns 200 if all components healthy, 200 with degraded status otherwise.
    Load balancers should check `status` field: "healthy" | "degraded".
    """
    db_health = await _check_database()
    redis_health = await _check_redis()
    llm_health = await _check_llm_providers()

    components = {
        "database": db_health,
        "redis": redis_health,
        "llm_providers": llm_health,
    }

    all_ok = all(c.get("status") == "ok" for c in components.values())

    return {
        "status": "healthy" if all_ok else "degraded",
        "components": components,
        "version": _get_version(),
    }


@router.get("/health/live")
async def liveness_probe():
    """Kubernetes-style liveness probe. Always returns 200 if the process is alive."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_probe():
    """Kubernetes-style readiness probe. Returns 200 only if the database is reachable."""
    db_health = await _check_database()
    if db_health["status"] != "ok":
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "not_ready", "database": db_health})
    return {"status": "ready"}


def _get_version() -> str:
    try:
        from app.core.config import settings
        return getattr(settings, "VERSION", "unknown")
    except Exception:
        return "unknown"
