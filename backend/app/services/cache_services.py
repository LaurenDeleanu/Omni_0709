import logging
import hashlib
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set

logger = logging.getLogger("successcore.cache_services")

EMBEDDING_CACHE_NAMESPACE = "embeddings"
EMBEDDING_CACHE_TTL = 86400

QUERY_CACHE_NAMESPACE = "rag_query"
QUERY_CACHE_TTL = 600

ROUTE_CACHE_NAMESPACE = "model_routing"
ROUTE_CACHE_TTL = 300


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


async def get_cached_embedding(text: str) -> Optional[List[float]]:
    key = _text_hash(text)
    try:
        return await cache_get(EMBEDDING_CACHE_NAMESPACE, key)
    except Exception as e:
        logger.debug(f"Embedding cache miss: {e}")
        return None


async def set_cached_embedding(text: str, embedding: List[float]):
    key = _text_hash(text)
    try:
        await cache_set(EMBEDDING_CACHE_NAMESPACE, key, embedding, ttl=EMBEDDING_CACHE_TTL)
    except Exception as e:
        logger.debug(f"Embedding cache set failed: {e}")


async def get_cached_rag_query(agent_id: str, query: str, limit: int) -> Optional[List[Dict[str, Any]]]:
    cache_key = f"{agent_id}:{_text_hash(query)}:{limit}"
    try:
        return await cache_get(QUERY_CACHE_NAMESPACE, cache_key)
    except Exception:
        return None


async def set_cached_rag_query(agent_id: str, query: str, limit: int, results: List[Dict[str, Any]]):
    cache_key = f"{agent_id}:{_text_hash(query)}:{limit}"
    try:
        await cache_set(QUERY_CACHE_NAMESPACE, cache_key, results, ttl=QUERY_CACHE_TTL)
    except Exception as e:
        logger.debug(f"RAG query cache set failed: {e}")


async def get_cached_routing(user_message: str, budget: bool) -> Optional[Dict[str, Any]]:
    cache_key = f"{_text_hash(user_message)}:{budget}"
    try:
        return await cache_get(ROUTE_CACHE_NAMESPACE, cache_key)
    except Exception:
        return None


async def set_cached_routing(user_message: str, budget: bool, decision: Dict[str, Any]):
    cache_key = f"{_text_hash(user_message)}:{budget}"
    try:
        await cache_set(ROUTE_CACHE_NAMESPACE, cache_key, decision, ttl=ROUTE_CACHE_TTL)
    except Exception as e:
        logger.debug(f"Routing cache set failed: {e}")
