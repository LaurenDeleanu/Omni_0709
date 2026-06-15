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
    
    try:
        tenants, settings = asyncio.run(get_tenants())
    except Exception as e:
        logger.error(f"Failed to fetch tenants: {e}")
        return

    if not tenants:
        logger.info("No active tenants found")
        return

    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))

    for tenant in tenants:
        schema = f"tenant_{tenant.schema_name}" if not settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite") else None
        if schema:
            logger.info(f"Migrating tenant schema: {schema}")
            try:
                # Pass schema to env.py via attributes
                alembic_cfg.attributes["tenant_schema"] = schema
                # Run upgrade synchronously
                command.upgrade(alembic_cfg, "head")
                logger.info(f"  Done: {tenant.name} ({schema})")
            except Exception as e:
                logger.error(f"  Failed: {tenant.name} ({schema}): {e}")
        else:
            logger.info(f"Skipping SQLite tenant: {tenant.name}")

    logger.info("All tenant migrations complete")

if __name__ == "__main__":
    run_migrations_for_all_tenants()
