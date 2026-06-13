import time
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis

logger = logging.getLogger("successcore.agent_pool")

POOL_METADATA_PREFIX = "pool:"
POOL_QUEUE_PREFIX = "pool_queue:"
POOL_TTL_AGENT_SECONDS = 600
POOL_CLEANUP_INTERVAL = 120
POOL_SCALE_CHECK_INTERVAL = 60
DEFAULT_POOL_SIZE = 3
MAX_POOL_SIZE = 10
MIN_POOL_SIZE = 1


@dataclass
class PoolAgent:
    agent_id: str
    db_session: Optional[AsyncSession] = None
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    last_used_at: float = 0.0

    def is_expired(self, max_age_seconds: int = POOL_TTL_AGENT_SECONDS) -> bool:
        return (time.monotonic() - self.created_at) > max_age_seconds

    def clear_user_context(self):
        self.context_snapshot = {}
        self.last_used_at = time.monotonic()


class AgentPool:
    def __init__(self, agent_id: str, pool_size: int = DEFAULT_POOL_SIZE, warm_cold_start_ms: int = 2000):
        self.agent_id = agent_id
        self.pool_size = pool_size
        self.warm_cold_start_ms = warm_cold_start_ms
        self._available: List[PoolAgent] = []
        self._in_use: Dict[str, PoolAgent] = {}
        self._lock = asyncio.Lock()
        self.warm_starts = 0
        self.cold_starts = 0
        self._warm_latencies: List[float] = []
        self._cold_latencies: List[float] = []

    async def get_agent(self, db_factory=None) -> PoolAgent:
        async with self._lock:
            now = time.monotonic()
            if self._available:
                agent = self._available.pop()
                agent.clear_user_context()
                agent.last_used_at = now
                self._in_use[agent.agent_id] = agent
                self.warm_starts += 1
                self._warm_latencies.append(0.0)
                logger.debug(f"Pool warm start for agent {self.agent_id}, available: {len(self._available)}, in_use: {len(self._in_use)}")
                return agent

            start = time.monotonic()
            agent = PoolAgent(
                agent_id=self.agent_id,
                db_session=None,
                context_snapshot={},
                created_at=now,
                last_used_at=now,
            )
            self._in_use[self.agent_id] = agent
            self.cold_starts += 1
            cold_latency = (time.monotonic() - start) * 1000
            self._cold_latencies.append(cold_latency)
            logger.debug(f"Pool cold start for agent {self.agent_id}, in_use: {len(self._in_use)}")
            return agent

    async def return_agent(self, agent: PoolAgent):
        async with self._lock:
            agent_key = agent.agent_id
            if agent_key in self._in_use:
                del self._in_use[agent_key]

            if agent.is_expired():
                logger.debug(f"Agent aged out, expired: {agent_key}")
                return

            agent.clear_user_context()

            if len(self._available) < self.pool_size:
                self._available.append(agent)
            logger.debug(f"Agent returned to pool {self.agent_id}, available: {len(self._available)}, in_use: {len(self._in_use)}")

    async def get_pool_stats(self) -> dict:
        async with self._lock:
            avg_warm = sum(self._warm_latencies) / len(self._warm_latencies) if self._warm_latencies else 0
            avg_cold = sum(self._cold_latencies) / len(self._cold_latencies) if self._cold_latencies else 0
            return {
                "pool_size": self.pool_size,
                "available_count": len(self._available),
                "in_use_count": len(self._in_use),
                "warm_starts": self.warm_starts,
                "cold_starts": self.cold_starts,
                "avg_warm_latency_ms": round(avg_warm, 2),
                "avg_cold_latency_ms": round(avg_cold, 2),
            }

    async def evict_expired(self):
        async with self._lock:
            before = len(self._available)
            self._available = [a for a in self._available if not a.is_expired()]
            expired = before - len(self._available)
            if expired:
                logger.debug(f"Evicted {expired} expired agents from pool {self.agent_id}")

    async def resize(self, new_size: int):
        new_size = max(MIN_POOL_SIZE, min(MAX_POOL_SIZE, new_size))
        async with self._lock:
            self.pool_size = new_size
            if len(self._available) > self.pool_size:
                self._available = self._available[: self.pool_size]
        logger.info(f"Pool {self.agent_id} resized to {new_size}")


class AgentPoolManager:
    _pools: Dict[str, AgentPool] = {}
    _lock = asyncio.Lock()
    _last_scale_check: Dict[str, float] = {}

    @classmethod
    async def get_pool(cls, agent_id: str, db: Optional[AsyncSession] = None) -> AgentPool:
        async with cls._lock:
            if agent_id not in cls._pools:
                pool_size = await cls._calculate_pool_size(agent_id)
                cls._pools[agent_id] = AgentPool(agent_id=agent_id, pool_size=pool_size)
                logger.info(f"Created agent pool for {agent_id} with size {pool_size}")

                pool = cls._pools[agent_id]
                stats = await pool.get_pool_stats()
                await cls._store_pool_metadata(agent_id, stats)
            else:
                pool = cls._pools[agent_id]

            now = time.time()
            last_check = cls._last_scale_check.get(agent_id, 0)
            if now - last_check > POOL_SCALE_CHECK_INTERVAL:
                cls._last_scale_check[agent_id] = now
                queue_depth = await cls._get_queue_depth(agent_id)
                await cls.auto_scale_based_on_queue(agent_id, queue_depth)

            return pool

    @classmethod
    async def scale_pool(cls, agent_id: str, target_size: int):
        pool = cls._pools.get(agent_id)
        if pool:
            await pool.resize(target_size)
        else:
            size = max(MIN_POOL_SIZE, min(MAX_POOL_SIZE, target_size))
            cls._pools[agent_id] = AgentPool(agent_id=agent_id, pool_size=size)
            logger.info(f"Scaled pool for {agent_id} to size {size}")

        await cls._store_pool_metadata(agent_id, {"pool_size": target_size})

    @classmethod
    async def auto_scale_based_on_queue(cls, agent_id: str, queue_depth: int):
        pool = cls._pools.get(agent_id)
        if not pool:
            return

        if queue_depth > 5:
            target = min(queue_depth, MAX_POOL_SIZE)
            await pool.resize(target)
            logger.info(f"Auto-scaled pool {agent_id} UP to {target} (queue_depth={queue_depth})")
        elif queue_depth == 0:
            r = await get_redis()
            last_active_key = f"{POOL_METADATA_PREFIX}{agent_id}:last_queue_active"
            last_active = await r.get(last_active_key)
            now = time.time()
            if last_active:
                idle_seconds = now - float(last_active)
                if idle_seconds > 300:
                    await pool.resize(MIN_POOL_SIZE)
                    logger.info(f"Auto-scaled pool {agent_id} DOWN to {MIN_POOL_SIZE} (idle for {idle_seconds:.0f}s)")

        pool_stats = await pool.get_pool_stats()
        await cls._store_pool_metadata(agent_id, pool_stats)

    @classmethod
    async def _get_queue_depth(cls, agent_id: str) -> int:
        try:
            r = await get_redis()
            key = f"{POOL_QUEUE_PREFIX}{agent_id}"
            length = await r.llen(key)
            return length
        except Exception:
            return 0

    @classmethod
    async def _calculate_pool_size(cls, agent_id: str) -> int:
        queue_depth = await cls._get_queue_depth(agent_id)
        if queue_depth > 5:
            return min(queue_depth, MAX_POOL_SIZE)
        return DEFAULT_POOL_SIZE

    @classmethod
    async def _store_pool_metadata(cls, agent_id: str, stats: dict):
        try:
            r = await get_redis()
            key = f"{POOL_METADATA_PREFIX}{agent_id}:stats"
            await r.set(key, json.dumps(stats))
            await r.expire(key, 3600)
        except Exception as e:
            logger.warning(f"Failed to store pool metadata: {e}")

    @classmethod
    async def get_all_pool_stats(cls) -> Dict[str, Dict]:
        result = {}
        for agent_id, pool in cls._pools.items():
            result[agent_id] = await pool.get_pool_stats()
        return result
