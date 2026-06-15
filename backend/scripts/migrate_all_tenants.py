#!/usr/bin/env python3
import os
import sys
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_tenants")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


async def get_tenants():
    from app.core.config import settings
    from app.core.database import AsyncSessionGlobal
    from app.models.tenant import Tenant
    from sqlalchemy import select

    async with AsyncSessionGlobal() as db:
        result = await db.execute(select(Tenant).where(Tenant.is_active == True))
        tenants = result.scalars().all()
    return tenants, settings

def run_migrations_for_all_tenants():
    from alembic.config import Config
    from alembic import command
    from app.core.database import engine
    from app.models.base import GlobalBase, Base
    from sqlalchemy import text
    import asyncio
    
    async def run_db_operations():
        # 1. Global tables
        try:
            async with engine.begin() as conn:
                await conn.run_sync(GlobalBase.metadata.create_all)
            logger.info("Global tables created/verified")
        except Exception as e:
            logger.error(f"Failed to create global tables: {e}")
            raise

        # 2. Fetch tenants
        from app.core.config import settings
        from app.core.database import AsyncSessionGlobal
        from app.models.tenant import Tenant
        from sqlalchemy import select

        async with AsyncSessionGlobal() as db:
            result = await db.execute(select(Tenant).where(Tenant.is_active == True))
            tenants = result.scalars().all()
        
        return tenants, settings

    try:
        tenants, settings = asyncio.run(run_db_operations())
    except Exception as e:
        logger.error(f"Failed to prepare database: {e}")
        return

    if not tenants:
        logger.info("No active tenants found")
        return

    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    
    async def create_tenant_tables(uri: str, schema: str):
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.models.base import Base
        from sqlalchemy import text
        
        # Create a fresh engine for this loop iteration
        tenant_engine = create_async_engine(uri).execution_options(schema_translate_map={None: schema})
        async with tenant_engine.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
            await conn.run_sync(Base.metadata.create_all)
        await tenant_engine.dispose()

    for tenant in tenants:
        schema = f"tenant_{tenant.schema_name}" if not settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite") else None
        if schema:
            logger.info(f"Migrating tenant schema: {schema}")
            try:
                # 1. Create schema and base tables using fresh engine
                asyncio.run(create_tenant_tables(settings.SQLALCHEMY_DATABASE_URI, schema))
                
                # 2. Run alembic upgrade (which creates its own event loop internally)
                alembic_cfg.attributes["tenant_schema"] = schema
                command.upgrade(alembic_cfg, "head")
                logger.info(f"  Done: {tenant.name} ({schema})")
            except Exception as e:
                logger.error(f"  Failed: {tenant.name} ({schema}): {e}")
        else:
            logger.info(f"Skipping SQLite tenant: {tenant.name}")

    # Dispose global engine
    asyncio.run(engine.dispose())

    logger.info("All tenant migrations complete")

if __name__ == "__main__":
    run_migrations_for_all_tenants()
