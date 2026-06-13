import time
import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger("successcore.fallback")

DEFAULT_CASCADE = [
    {"model": "nvidia/nemotron-3-ultra-550b-a55b:free", "provider": "openrouter"},      # 1M ctx, 550B params
    {"model": "nvidia/nemotron-3-super-120b-a12b:free", "provider": "openrouter"},      # 1M ctx, structured outputs
    {"model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", "provider": "openrouter"},  # 256K ctx, reasoning
    {"model": "nvidia/nemotron-3-nano-30b-a3b:free", "provider": "openrouter"},         # 256K ctx, fast
    {"model": "qwen/qwen3-next-80b-a3b-instruct:free", "provider": "openrouter"},       # 262K ctx, structured
]

CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_COOLDOWN = 30


class ProviderHealthTracker:
    """Tracks provider health for circuit-breaker logic.

    Uses ``asyncio.Lock`` (instead of ``threading.Lock``) so that calls
    to ``record_success`` / ``record_failure`` / ``is_healthy`` never block
    the event loop when running inside FastAPI.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._consecutive_failures: Dict[str, int] = defaultdict(int)
        self._last_failure_time: Dict[str, float] = {}
        self._total_attempts: Dict[str, int] = defaultdict(int)
        self._total_failures: Dict[str, int] = defaultdict(int)
        self._total_latency_ms: Dict[str, float] = defaultdict(float)

    async def record_success(self, provider: str, latency_ms: float = 0):
        async with self._lock:
            self._consecutive_failures[provider] = 0
            self._total_attempts[provider] += 1
            self._total_latency_ms[provider] += latency_ms

    async def record_failure(self, provider: str):
        async with self._lock:
            self._consecutive_failures[provider] += 1
            self._last_failure_time[provider] = time.monotonic()
            self._total_attempts[provider] += 1
            self._total_failures[provider] += 1

    async def is_healthy(self, provider: str) -> bool:
        async with self._lock:
            failures = self._consecutive_failures.get(provider, 0)
            if failures < CIRCUIT_BREAKER_THRESHOLD:
                return True
            last_fail = self._last_failure_time.get(provider, 0)
            if time.monotonic() - last_fail > CIRCUIT_BREAKER_COOLDOWN:
                self._consecutive_failures[provider] = 0
                return True
            return False

    async def get_stats(self, provider: str) -> dict:
        async with self._lock:
            total = self._total_attempts.get(provider, 0)
            failures = self._total_failures.get(provider, 0)
            latency = self._total_latency_ms.get(provider, 0)
        healthy = await self.is_healthy(provider)
        return {
            "provider": provider,
            "healthy": healthy,
            "total_attempts": total,
            "total_failures": failures,
            "error_rate": round(failures / max(total, 1), 4),
            "avg_latency_ms": round(latency / max(total, 1), 1),
            "circuit_open": not healthy,
        }

    async def get_all_stats(self) -> List[dict]:
        async with self._lock:
            providers = set()
            providers.update(self._total_attempts.keys())
            providers.update(self._consecutive_failures.keys())
        return [await self.get_stats(p) for p in providers]


_provider_health = ProviderHealthTracker()


def get_provider_health() -> ProviderHealthTracker:
    return _provider_health


def get_provider_for_model(model_name: str) -> str:
    model_lower = model_name.lower()
    if "/" in model_lower or "openrouter" in model_lower:
        return "openrouter"
    elif "gemini" in model_lower:
        return "gemini"
    elif "claude" in model_lower or "anthropic" in model_lower:
        return "anthropic"
    elif "groq" in model_lower:
        return "groq"
    elif "llama" in model_lower or "meta" in model_lower:
        return "openrouter"
    else:
        return "openai"


def parse_fallback_models(agent) -> List[dict]:
    cascade: List[dict] = []
    if agent and agent.agent_settings:
        raw = agent.agent_settings.get("ai_fallback_models")
        if raw:
            import json
            try:
                if isinstance(raw, str):
                    models = json.loads(raw)
                else:
                    models = raw
                if isinstance(models, list):
                    for m in models:
                        if isinstance(m, str):
                            cascade.append({"model": m, "provider": get_provider_for_model(m)})
                        elif isinstance(m, dict) and "model" in m:
                            cascade.append(m)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse ai_fallback_models for agent {agent.id}")
    return cascade


def build_full_cascade(primary_model: str, agent, agent_model: str = None) -> List[dict]:
    cascade = [{"model": primary_model, "provider": get_provider_for_model(primary_model)}]
    if agent_model and agent_model != primary_model:
        cascade.append({"model": agent_model, "provider": get_provider_for_model(agent_model)})
    fallback = parse_fallback_models(agent)
    for fb in fallback:
        if fb["model"] not in [c["model"] for c in cascade]:
            cascade.append(fb)
    for default in DEFAULT_CASCADE:
        if default["model"] not in [c["model"] for c in cascade]:
            cascade.append(default)
    return cascade


async def resolve_provider_client(model_name: str, agent, db):
    from app.services.llm_router import get_llm_client as _get_client
    return await _get_client(model_name, agent, db)
