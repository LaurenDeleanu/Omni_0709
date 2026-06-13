import logging
import json
from typing import List, Dict, Any
from app.core.config import settings

logger = logging.getLogger("successcore.rerank")

async def rerank_chunks(
    chunks: List[Dict[str, Any]],
    query_text: str,
    agent: Any = None,
    final_limit: int = 3,
) -> List[Dict[str, Any]]:
    """
    Reranks a list of knowledge chunks using Cohere, LLM-based scoring, or keyword overlap.
    """
    if not chunks:
        return []
    if len(chunks) <= 1:
        return chunks[:final_limit]

    # Resolve Cohere API Key from settings or agent settings
    cohere_key = getattr(settings, "COHERE_API_KEY", "")
    if agent and agent.agent_settings:
        from app.core.encryption import decrypt_key
        raw_key = agent.agent_settings.get("cohere_api_key")
        if raw_key:
            cohere_key = decrypt_key(raw_key)

    # 1. Primary: Cohere Rerank API (Cross-Encoder)
    if cohere_key:
        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {cohere_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "rerank-multilingual-v3.0",
                "query": query_text,
                "documents": [c["content"] for c in chunks],
                "top_n": final_limit
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post("https://api.cohere.ai/v1/rerank", headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for result in data.get("results", []):
                        idx = result["index"]
                        relevance = result["relevance_score"]
                        results.append({**chunks[idx], "rerank_score": relevance})
                    results.sort(key=lambda x: x["rerank_score"], reverse=True)
                    logger.info("Cohere rerank completed successfully")
                    return results
        except Exception as e:
            logger.warning(f"Cohere rerank failed, falling back to LLM: {e}")

    # 2. Secondary: LLM-based Reranking
    try:
        from app.services.llm_router import get_llm_client
        client, _ = await get_llm_client("gpt-4o-mini", agent)
        
        doc_list = "\n".join([f"ID: {idx}\nText: {c['content']}" for idx, c in enumerate(chunks)])
        prompt = (
            "You are a search reranker. Evaluate the relevance of the following documents to the query.\n\n"
            f"Query: {query_text}\n\n"
            f"Documents:\n{doc_list}\n\n"
            "Respond strictly with a JSON object containing a 'ranked_indices' array of integers in order of relevance."
        )
        
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "rerank_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "ranked_indices": {
                            "type": "array",
                            "items": {"type": "integer"}
                        }
                    },
                    "required": ["ranked_indices"],
                    "additionalProperties": False
                },
                "strict": True
            }
        }
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
            response_format=response_format
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        indices = data.get("ranked_indices", [])
        
        if isinstance(indices, list):
            results = []
            for rank, idx in enumerate(indices):
                if isinstance(idx, int) and 0 <= idx < len(chunks):
                    score = 1.0 - (rank / len(indices))
                    results.append({**chunks[idx], "rerank_score": score})
            # Add any missing chunks at the end
            for idx, c in enumerate(chunks):
                if not any(r["chunk_id"] == c.get("chunk_id", c.get("id")) for r in results):
                    results.append({**c, "rerank_score": 0.0})
            results.sort(key=lambda x: x["rerank_score"], reverse=True)
            logger.info("LLM rerank completed successfully")
            return results[:final_limit]
    except Exception as e:
        logger.warning(f"LLM rerank failed, falling back to heuristic: {e}")

    # 3. Tertiary Fallback: Keyword Overlap + Similarity scoring
    scored = []
    for chunk in chunks:
        overlap = _compute_keyword_overlap(query_text, chunk["content"])
        recency_bonus = 0.0
        meta = chunk.get("metadata")
        if isinstance(meta, dict):
            chunk_idx = meta.get("chunk_index", 0)
            total = meta.get("total_chunks", 1)
            recency_bonus = (chunk_idx / max(total, 1)) * 0.05
        score = chunk.get("similarity", 0.0) * 0.7 + overlap * 0.25 + recency_bonus
        scored.append({**chunk, "rerank_score": round(score, 4)})

    scored.sort(key=lambda c: c["rerank_score"], reverse=True)
    logger.info("Heuristic keyword-overlap rerank completed")
    return scored[:final_limit]


def _compute_keyword_overlap(query: str, text: str) -> float:
    query_words = set(query.lower().split())
    text_words = set(text.lower().split())
    if not query_words:
        return 0.0
    overlap = query_words & text_words
    return len(overlap) / len(query_words)
