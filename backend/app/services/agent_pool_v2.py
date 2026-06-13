import logging
import json
import uuid
import time
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import Agent, AgentConfig, AgentExecutionRun

logger = logging.getLogger("successcore.agent_pool_v2")


@dataclass
class PoolAgent:
    id: str
    agent_type: str
    name: str
    created_at: float
    last_used_at: float
    total_runs: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0


@dataclass
class PoolStats:
    pool_size: int
    active_agents: int
    idle_agents: int
    total_runs: int
    avg_agent_latency_ms: float
    agent_types: Dict[str, int]


class AgentPoolV2:
    def __init__(self, max_idle_per_type: int = 3, max_total: int = 30, idle_ttl_seconds: int = 300):
        self._agents: Dict[str, PoolAgent] = {}
        self._lock = asyncio.Lock()
        self.max_idle_per_type = max_idle_per_type
        self.max_total = max_total
        self.idle_ttl_seconds = idle_ttl_seconds
        self._cleanup_task: Optional[asyncio.Task] = None
        self._stats: Dict[str, int] = {"total_runs": 0, "total_errors": 0, "cache_hits": 0, "cache_misses": 0}

    async def get_or_create(
        self,
        db: AsyncSession,
        agent_type: str,
        system_prompt: str,
        tools: Optional[List[str]] = None,
        model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    ) -> Agent:
        async with self._lock:
            now = time.monotonic()
            idle_pool = [
                pa for pa in self._agents.values()
                if pa.agent_type == agent_type
                and now - pa.last_used_at < self.idle_ttl_seconds
            ]
            idle_pool.sort(key=lambda pa: pa.last_used_at)

            if idle_pool:
                pool_agent = idle_pool[-1]
                pool_agent.last_used_at = now
                pool_agent.total_runs += 1
                self._stats["cache_hits"] += 1
                logger.debug(f"AgentPool: reusing {pool_agent.name} ({pool_agent.id[:8]}) for {agent_type}")
                agent_res = await db.execute(select(Agent).where(Agent.id == pool_agent.id))
                agent = agent_res.scalar_one_or_none()
                if agent:
                    return agent

            self._stats["cache_misses"] += 1
            return await self._create_agent(db, agent_type, system_prompt, tools, model)

    async def _create_agent(
        self,
        db: AsyncSession,
        agent_type: str,
        system_prompt: str,
        tools: Optional[List[str]] = None,
        model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    ) -> Agent:
        now = time.monotonic()
        agent_id = uuid.uuid4().hex

        agent = Agent(
            id=agent_id,
            name=f"Pool-{agent_type}-{agent_id[:6]}",
            avatar="",
            agent_type=agent_type.upper(),
            ai_model=model,
            ai_system_prompt=system_prompt,
            ai_temperature=0.2,
            ai_tone="Profesional",
            agent_settings={
                "ai_tools": json.dumps(tools if tools else []),
                "pool_managed": True,
                "pool_type": agent_type,
            },
        )
        db.add(agent)
        await db.flush()

        config = AgentConfig(
            id=uuid.uuid4().hex,
            agent_id=agent_id,
            max_loops=5,
            max_tokens_per_run=100000,
        )
        db.add(config)
        await db.flush()

        pool_agent = PoolAgent(
            id=agent_id,
            agent_type=agent_type,
            name=agent.name,
            created_at=now,
            last_used_at=now,
            total_runs=1,
        )
        self._agents[agent_id] = pool_agent

        logger.info(f"AgentPool: created {agent.name} ({agent_id[:8]}) for type {agent_type}")
        return agent

    async def record_completion(self, agent_id: str, latency_ms: float):
        async with self._lock:
            pa = self._agents.get(agent_id)
            if pa:
                if pa.total_runs > 0:
                    pa.avg_latency_ms = (pa.avg_latency_ms * (pa.total_runs - 1) + latency_ms) / pa.total_runs
                else:
                    pa.avg_latency_ms = latency_ms
                self._stats["total_runs"] += 1

    async def record_error(self, agent_id: str):
        async with self._lock:
            pa = self._agents.get(agent_id)
            if pa:
                pa.total_errors += 1
                self._stats["total_errors"] += 1

    async def get_stats(self) -> PoolStats:
        async with self._lock:
            now = time.monotonic()
            active = len(self._agents)
            idle = sum(
                1 for pa in self._agents.values()
                if now - pa.last_used_at < self.idle_ttl_seconds
            )
            total_runs = sum(pa.total_runs for pa in self._agents.values())
            avg_latency = (
                sum(pa.avg_latency_ms for pa in self._agents.values()) / max(active, 1)
            )
            types_count: Dict[str, int] = {}
            for pa in self._agents.values():
                types_count[pa.agent_type] = types_count.get(pa.agent_type, 0) + 1

            return PoolStats(
                pool_size=active,
                active_agents=active - idle,
                idle_agents=idle,
                total_runs=total_runs,
                avg_agent_latency_ms=round(avg_latency, 1),
                agent_types=types_count,
            )

    async def prune_idle(self):
        async with self._lock:
            now = time.monotonic()
            expired = [
                aid for aid, pa in self._agents.items()
                if now - pa.last_used_at > self.idle_ttl_seconds * 2
            ]
            for aid in expired:
                pa = self._agents.pop(aid, None)
                if pa:
                    logger.debug(f"AgentPool: pruned idle agent {pa.name} ({aid[:8]})")
            if expired:
                logger.info(f"AgentPool: pruned {len(expired)} idle agents")

    async def start_pruner(self, interval_seconds: int = 120):
        async def _prune_loop():
            while True:
                await asyncio.sleep(interval_seconds)
                await self.prune_idle()
        self._cleanup_task = asyncio.ensure_future(_prune_loop())

    async def stop_pruner(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


agent_pool_v2 = AgentPoolV2()
