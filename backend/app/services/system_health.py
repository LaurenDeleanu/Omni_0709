import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("successcore.syshealth")


async def get_system_health(db: AsyncSession) -> Dict[str, Any]:
    from app.core.database import engine

    pool = engine.pool
    pool_status = {}
    if hasattr(pool, "size"):
        pool_status["size"] = pool.size()
    if hasattr(pool, "checkedin"):
        pool_status["checked_in"] = pool.checkedin()
    if hasattr(pool, "overflow"):
        pool_status["overflow"] = pool.overflow()

    from app.services.api_analytics import get_analytics
    analytics = get_analytics()

    from app.services.llm_cache import cache_stats
    from app.services.model_fallback import get_provider_health

    return {
        "database_pool": pool_status,
        "api_requests": analytics.get("total_requests", 0),
        "unique_clients": analytics.get("unique_clients", 0),
        "llm_cache": cache_stats(),
        "provider_health": get_provider_health().get_all_stats(),
    }
