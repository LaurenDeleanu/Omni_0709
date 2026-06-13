#!/usr/bin/env python3
import os
import sys
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_tenants")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


async def run_migrations_for_all_tenants():
    from app.core.config import settings
    from app.core.database import engine, AsyncSessionGlobal
    from app.models.tenant import Tenant
    from sqlalchemy import text, select
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "backend", "alembic.ini"))

    async with AsyncSessionGlobal() as db:
        result = await db.execute(select(Tenant).where(Tenant.is_active == True))
        tenants = result.scalars().all()

    if not tenants:
        logger.info("No active tenants found")
        return

    for tenant in tenants:
        schema = f"tenant_{tenant.schema_name}" if not settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite") else None
        if schema:
            logger.info(f"Migrating tenant schema: {schema}")
            try:
                async with engine.begin() as conn:
                    await conn.execute(text(f"SET search_path TO {schema}"))
                    await conn.run_sync(lambda c: command.upgrade(alembic_cfg, "head"))
                logger.info(f"  Done: {tenant.name} ({schema})")
            except Exception as e:
                logger.error(f"  Failed: {tenant.name} ({schema}): {e}")
        else:
            logger.info(f"Skipping SQLite tenant: {tenant.name}")

    logger.info("All tenant migrations complete")


if __name__ == "__main__":
    asyncio.run(run_migrations_for_all_tenants())
