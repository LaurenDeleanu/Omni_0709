import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.search_index import SearchIndexEntry
from app.services.embedding_providers import generate_embedding

logger = logging.getLogger(__name__)

async def index_entity(
    db: AsyncSession,
    entity_id: str,
    entity_type: str,
    title: str,
    subtitle: str,
    content: str,
    route: str,
) -> SearchIndexEntry:
    """
    Creates or updates the search index entry for a given entity, generating its embedding.
    """
    logger.info("Indexing entity %s of type %s", entity_id, entity_type)
    
    # Compile text for embedding: title + subtitle + content
    embedding_text = f"{title}\n{subtitle or ''}\n{content}".strip()
    
    # Generate embedding
    try:
        embedding = await generate_embedding(embedding_text)
    except Exception as e:
        logger.warning("Failed to generate embedding for entity %s (%s): %s. Storing without embedding.", entity_id, entity_type, e)
        embedding = None
        
    # Check if entry already exists
    stmt = select(SearchIndexEntry).where(
        SearchIndexEntry.entity_id == entity_id,
        SearchIndexEntry.entity_type == entity_type
    )
    res = await db.execute(stmt)
    entry = res.scalars().first()
    
    if entry:
        entry.title = title
        entry.subtitle = subtitle
        entry.content = content
        entry.route = route
        entry.embedding = embedding
    else:
        entry = SearchIndexEntry(
            entity_id=entity_id,
            entity_type=entity_type,
            title=title,
            subtitle=subtitle,
            content=content,
            route=route,
            embedding=embedding
        )
        db.add(entry)
        
    await db.flush()
    return entry

async def delete_entity_index(
    db: AsyncSession,
    entity_id: str,
    entity_type: str
) -> None:
    """
    Deletes the search index entry for a given entity.
    """
    logger.info("Deleting search index for entity %s (%s)", entity_id, entity_type)
    stmt = delete(SearchIndexEntry).where(
        SearchIndexEntry.entity_id == entity_id,
        SearchIndexEntry.entity_type == entity_type
    )
    await db.execute(stmt)
    await db.flush()
