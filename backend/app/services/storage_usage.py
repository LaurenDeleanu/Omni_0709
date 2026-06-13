import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("successcore.storage")


async def get_tenant_storage_usage(db: AsyncSession) -> dict:
    from sqlalchemy import text as sa_text

    result = await db.execute(sa_text("SELECT pg_database_size(current_database())"))
    db_size_bytes = result.scalar() or 0

    result = await db.execute(sa_text("SELECT pg_size_pretty(pg_database_size(current_database()))"))
    db_size_pretty = result.scalar() or "0 bytes"

    result = await db.execute(sa_text("""
        SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) 
        FROM pg_catalog.pg_statio_user_tables 
        ORDER BY pg_total_relation_size(relid) DESC 
        LIMIT 15
    """))
    table_sizes = [{"table": r[0], "size": r[1]} for r in result.all()]

    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
    uploads_size = 0
    uploads_count = 0
    if os.path.exists(uploads_dir):
        for dirpath, dirnames, filenames in os.walk(uploads_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                uploads_size += os.path.getsize(fp)
                uploads_count += 1

    return {
        "database": {"total_size": db_size_pretty, "total_bytes": db_size_bytes},
        "uploads": {"count": uploads_count, "size_mb": round(uploads_size / (1024 * 1024), 2)},
        "largest_tables": table_sizes,
    }
