#!/usr/bin/env python3
import os
import sys
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_tenants")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


async def get_tenants():
    from app.core.config import settings
    from app.core.database import AsyncSessionGlobal
    from app.models.tenant import Tenant
    from sqlalchemy import select

    async with AsyncSessionGlobal() as db:
        result = await db.execute(select(Tenant).where(Tenant.is_active == True))
        tenants = result.scalars().all()
    return tenants, settings

def run_migrations_global():
    from alembic.config import Config
    from alembic import command
    from app.core.database import engine
    from app.models.base import GlobalBase, Base
    import asyncio
    
    async def run_db_operations():
        try:
            async with engine.begin() as conn:
                await conn.run_sync(GlobalBase.metadata.create_all)
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    try:
        asyncio.run(run_db_operations())
    except Exception as e:
        logger.error(f"Failed to prepare database: {e}")
        return

    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    
    try:
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations complete")
    except Exception as e:
        logger.error(f"Migration failed: {e}")

    asyncio.run(engine.dispose())
    logger.info("Database ready")

if __name__ == "__main__":
    run_migrations_global()
