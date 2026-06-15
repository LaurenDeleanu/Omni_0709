import asyncio
from sqlalchemy import text
import sys
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reset_db")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.database import engine
from app.models.base import GlobalBase, Base

async def reset_db():
    logger.info("Wiping public schema...")
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE;"))
        await conn.execute(text("CREATE SCHEMA public;"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    
    logger.info("Recreating all tables from models...")
    async with engine.begin() as conn:
        await conn.run_sync(GlobalBase.metadata.create_all)
        await conn.run_sync(Base.metadata.create_all)
        
        # Apply RLS Policies
        logger.info("Applying RLS policies to all tables...")
        for table_name in Base.metadata.tables.keys():
            await conn.execute(text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"))
            await conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table_name};"))
            await conn.execute(text(
                f"CREATE POLICY tenant_isolation_policy ON {table_name} "
                f"AS PERMISSIVE FOR ALL "
                f"TO PUBLIC "
                f"USING (tenant_id = current_setting('app.current_tenant_id', true));"
            ))
            await conn.execute(text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;"))

async def main():
    await reset_db()
    logger.info("Database reset complete.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
