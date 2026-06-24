import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.base import is_sqlite
from app.models.search_index import SearchIndexEntry
from app.services.embedding_providers import generate_embedding

logger = logging.getLogger(__name__)

# Check if pgvector is available
try:
    from pgvector.sqlalchemy import Vector
    _pgvector_available = True
except ImportError:
    _pgvector_available = False

async def perform_semantic_search(query: str, db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Performs semantic search using pgvector when available.
    Falls back to text-based search (ILIKE) on SQLite or if embedding generation fails.
    """
    logger.info("Performing semantic search for query: %s", query)
    results = []
    
    use_vector = _pgvector_available and not is_sqlite
    
    if use_vector:
        try:
            # 1. Embed the search query
            query_embedding = await generate_embedding(query)
            
            # 2. Query SearchIndexEntry by cosine distance
            distance_expr = SearchIndexEntry.embedding.cosine_distance(query_embedding)
            stmt = (
                select(SearchIndexEntry, distance_expr.label("distance"))
                .order_by("distance")
                .limit(limit)
            )
            res = await db.execute(stmt)
            for row in res.all():
                entry = row[0]
                dist = row[1]
                score = max(0.0, 1.0 - float(dist)) if dist is not None else 0.5
                results.append({
                    "id": entry.entity_id,
                    "type": entry.entity_type,
                    "title": entry.title,
                    "subtitle": entry.subtitle or "",
                    "route": entry.route,
                    "score": round(score, 4)
                })
            return results
        except Exception as e:
            logger.error("Vector semantic search failed, falling back to keyword: %s", e, exc_info=True)
            await db.rollback()
            
    # Fallback to ILIKE keyword search on search_index_entries (SQLite or fallback)
    logger.info("Falling back to text-based keyword search on search_index_entries")
    stmt = (
        select(SearchIndexEntry)
        .where(
            (SearchIndexEntry.title.ilike(f"%{query}%")) |
            (SearchIndexEntry.subtitle.ilike(f"%{query}%")) |
            (SearchIndexEntry.content.ilike(f"%{query}%"))
        )
        .limit(limit)
    )
    res = await db.execute(stmt)
    entries = res.scalars().all()
    for entry in entries:
        results.append({
            "id": entry.entity_id,
            "type": entry.entity_type,
            "title": entry.title,
            "subtitle": entry.subtitle or "",
            "route": entry.route,
            "score": 0.5  # Fixed fallback score
        })
        
    return results
