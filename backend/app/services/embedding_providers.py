import logging
import httpx
from typing import List, Optional
from app.models.agent import Agent

logger = logging.getLogger("successcore.embeddings")

OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_EMBEDDING_DIM = 1536
GEMINI_EMBEDDING_MODEL = "text-embedding-004"
GEMINI_EMBEDDING_DIM = 768


async def generate_embedding_openai(text: str, api_key: str, model: str = OPENAI_EMBEDDING_MODEL) -> List[float]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"input": text, "model": model},
        )
        resp.raise_for_status()
        data = resp.json()
        vector = data["data"][0]["embedding"]
        return vector


async def generate_embedding_gemini(text: str, api_key: str, model: str = GEMINI_EMBEDDING_MODEL) -> List[float]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model.split('/')[-1]}:embedContent?key={api_key}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json={
            "model": f"models/{model.split('/')[-1]}",
            "content": {"parts": [{"text": text}]},
        })
        resp.raise_for_status()
        data = resp.json()
        vector = data["embedding"]["values"]
        if len(vector) == GEMINI_EMBEDDING_DIM:
            vector.extend([0.0] * (OPENAI_EMBEDDING_DIM - GEMINI_EMBEDDING_DIM))
        return vector


async def generate_embedding(
    text: str,
    provider: str = "gemini",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> List[float]:
    if provider == "openai":
        from app.core.config import settings
        key = api_key or settings.OPENAI_API_KEY
        if not key:
            raise ValueError("No OpenAI API key configured for embeddings")
        return await generate_embedding_openai(text, key, model or OPENAI_EMBEDDING_MODEL)

    elif provider == "gemini":
        from app.core.config import settings
        key = api_key or settings.GEMINI_API_KEY
        if not key:
            from app.services.llm_router import get_gemini_client_compatible
            try:
                _, key = await get_gemini_client_compatible(None)
            except Exception:
                key = None
                
        if key:
            try:
                return await generate_embedding_gemini(text, key, model or GEMINI_EMBEDDING_MODEL)
            except Exception as e:
                logger.warning(f"Gemini embedding failed, falling back to OpenAI: {e}")
                
        # Fallback to OpenAI
        key = settings.OPENAI_API_KEY
        if key:
            try:
                return await generate_embedding_openai(text, key, OPENAI_EMBEDDING_MODEL)
            except Exception as e:
                logger.warning(f"OpenAI embedding fallback failed: {e}")
                
        # If all fail, return a mock zero vector instead of crashing
        logger.error("All embedding providers failed, returning mock zero vector")
        return [0.0] * OPENAI_EMBEDDING_DIM

    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")


async def get_available_embedding_providers() -> List[dict]:
    providers = []
    from app.core.config import settings

    if settings.OPENAI_API_KEY:
        providers.append({
            "provider": "openai",
            "default_model": OPENAI_EMBEDDING_MODEL,
            "dimensions": OPENAI_EMBEDDING_DIM,
            "available": True,
        })
    else:
        providers.append({
            "provider": "openai",
            "default_model": OPENAI_EMBEDDING_MODEL,
            "dimensions": OPENAI_EMBEDDING_DIM,
            "available": False,
            "reason": "No API key configured",
        })

    if settings.GEMINI_API_KEY:
        providers.append({
            "provider": "gemini",
            "default_model": GEMINI_EMBEDDING_MODEL,
            "dimensions": GEMINI_EMBEDDING_DIM,
            "available": True,
        })
    else:
        providers.append({
            "provider": "gemini",
            "default_model": GEMINI_EMBEDDING_MODEL,
            "dimensions": GEMINI_EMBEDDING_DIM,
            "available": False,
            "reason": "No API key configured",
        })

    return providers
