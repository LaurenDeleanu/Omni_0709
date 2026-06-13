# app/services/llm_cache.py — Multi-tier LLM response caching
# Tier 1: Exact-match cache (hash of model+messages+tools) — Redis-backed, 10min TTL
# Tier 2: Semantic template cache (parameterized prompts) — Redis-backed, 30min TTL
import hashlib
import json
import logging
import re
from typing import Optional, Any
from app.core.cache import cache_get, cache_set, cache_delete

logger = logging.getLogger("successcore.llmcache")

EXACT_NAMESPACE = "llm_exact"
TEMPLATE_NAMESPACE = "llm_template"
EXACT_TTL = 600   # 10 min
TEMPLATE_TTL = 1800  # 30 min


def _hash_key(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _make_exact_key(model: str, messages: list, tools: Optional[list] = None) -> str:
    normal = json.dumps({"model": model, "messages": messages, "tools": tools}, sort_keys=True, default=str)
    return _hash_key(normal)


def _extract_template_params(messages: list) -> Optional[str]:
    """Extract a parameterized template signature by replacing dynamic values with placeholders."""
    cleaned = []
    for msg in messages:
        content = str(msg.get("content", ""))
        # Replace UUIDs, emails, dates, numbers with placeholders
        content = re.sub(r'\b[a-f0-9]{32}\b', '{UUID}', content)
        content = re.sub(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', '{EMAIL}', content)
        content = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '{DATE}', content)
        content = re.sub(r'\b\d+\b', '{NUM}', content)
        cleaned.append({"role": msg.get("role", "user"), "tmpl": content})
    if not cleaned:
        return None
    return json.dumps(cleaned, sort_keys=True)


def _make_template_key(model: str, messages: list) -> Optional[str]:
    tmpl = _extract_template_params(messages)
    if not tmpl:
        return None
    return f"{model}:{_hash_key(tmpl)}"


# ── Tier 1: Exact-match cache ──────────────────────────────────────────────────

async def exact_cache_get(model: str, messages: list, tools: Optional[list] = None) -> Optional[Any]:
    key = _make_exact_key(model, messages, tools)
    return await cache_get(EXACT_NAMESPACE, key)


async def exact_cache_set(model: str, messages: list, tools: Optional[list], value: Any) -> None:
    key = _make_exact_key(model, messages, tools)
    await cache_set(EXACT_NAMESPACE, key, value, ttl=EXACT_TTL)


# ── Tier 2: Template-based cache ───────────────────────────────────────────────

async def template_cache_get(model: str, messages: list) -> Optional[Any]:
    key = _make_template_key(model, messages)
    if not key:
        return None
    return await cache_get(TEMPLATE_NAMESPACE, key)


async def template_cache_set(model: str, messages: list, value: Any) -> None:
    key = _make_template_key(model, messages)
    if not key:
        return
    await cache_set(TEMPLATE_NAMESPACE, key, value, ttl=TEMPLATE_TTL)


# ── Unified cache lookup (try exact → template → None) ──────────────────────────

async def llm_cache_lookup(model: str, messages: list, tools: Optional[list] = None) -> Optional[Any]:
    result = await exact_cache_get(model, messages, tools)
    if result is not None:
        logger.debug("LLM cache hit: exact")
        return result
    result = await template_cache_get(model, messages)
    if result is not None:
        logger.debug("LLM cache hit: template")
        return result
    return None


async def llm_cache_store(model: str, messages: list, tools: Optional[list], value: Any) -> None:
    await exact_cache_set(model, messages, tools, value)
    if tools is None:
        await template_cache_set(model, messages, value)


async def cache_invalidate(pattern: str = "") -> None:
    if pattern:
        await cache_delete(EXACT_NAMESPACE, pattern)
        await cache_delete(TEMPLATE_NAMESPACE, pattern)


async def cache_stats() -> dict:
    try:
        from app.core.redis import get_redis
        r = await get_redis()
        exact_count = 0
        template_count = 0
        cursor = 0
        while True:
            cursor, keys = await r.scan(cursor=cursor, match=f"cache:{EXACT_NAMESPACE}:*", count=100)
            exact_count += len(keys)
            if cursor == 0:
                break
        cursor = 0
        while True:
            cursor, keys = await r.scan(cursor=cursor, match=f"cache:{TEMPLATE_NAMESPACE}:*", count=100)
            template_count += len(keys)
            if cursor == 0:
                break
        return {
            "exact_cache_entries": exact_count,
            "template_cache_entries": template_count,
            "total_cached_responses": exact_count + template_count,
        }
    except Exception:
        return {"exact_cache_entries": 0, "template_cache_entries": 0, "total_cached_responses": 0, "error": "Redis unavailable"}
