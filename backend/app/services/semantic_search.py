import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.hire import JobPosting

logger = logging.getLogger(__name__)

async def perform_semantic_search(query: str, db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Mock implementation of semantic search.
    In a real scenario, this would:
    1. Embed the query using an LLM.
    2. Query a vector database (e.g., Redis vector similarity, pgvector, Pinecone).
    3. Return the semantically closest matches.
    """
    logger.info(f"Performing mock semantic search for query: {query}")
    results = []
    
    # Mocking semantic search behavior by just searching keywords broadly
    # and returning "semantic" looking results
    
    # Fallback to ILIKE for demonstration if we have no actual embeddings
    users_res = await db.execute(
        select(User).where(User.full_name.ilike(f"%{query}%")).limit(limit)
    )
    for u in users_res.scalars().all():
        results.append({
            "id": u.id,
            "type": "employee",
            "title": u.full_name or u.email,
            "subtitle": u.department or "",
            "route": f"/dashboard/employees/{u.id}",
            "score": 0.95  # Mock similarity score
        })
        
    jobs_res = await db.execute(
        select(JobPosting).where(JobPosting.title.ilike(f"%{query}%")).limit(limit)
    )
    for j in jobs_res.scalars().all():
        results.append({
            "id": j.id,
            "type": "job",
            "title": j.title,
            "subtitle": j.department or "",
            "route": f"/dashboard/hire/{j.id}",
            "score": 0.88  # Mock similarity score
        })
        
    # Sort by score descending (mocking vector similarity ordering)
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
