import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.services.agent_pool import AgentPoolManager

logger = logging.getLogger("successcore.pool_monitor")

def get_db_pool_stats() -> dict:
    from app.core.database import engine
    pool = engine.pool
    stats = {}
    if hasattr(pool, "size"):
        stats["size"] = pool.size()
    if hasattr(pool, "checkedin"):
        stats["checked_in"] = pool.checkedin()
    if hasattr(pool, "checkedout"):
        stats["checked_out"] = pool.checkedout()
    if hasattr(pool, "overflow"):
        stats["overflow"] = pool.overflow()
    stats["utilization_pct"] = round(stats.get("checked_out", 0) / max(stats.get("size", 1), 1) * 100, 1)
    return stats


async def monitor_agent_pools():
    """Background worker that continuously scales agent warm pools."""
    while True:
        try:
            # We iterate over all known agent pools and check their queue depth
            for agent_id, pool in AgentPoolManager._pools.items():
                queue_depth = await AgentPoolManager._get_queue_depth(agent_id)
                await AgentPoolManager.auto_scale_based_on_queue(agent_id, queue_depth)
                await pool.evict_expired()
        except Exception as e:
            logger.error(f"Agent pool monitor error: {e}")
            
        await asyncio.sleep(60)  # Check every 60 seconds

