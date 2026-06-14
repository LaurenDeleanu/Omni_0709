"""
tenant_context.py — Set PostgreSQL tenant context for RLS policies.
Call at the start of each tenant-scoped request to set app.current_tenant_id.
"""
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def set_tenant_context(db: AsyncSession, tenant_id: str):
    """Set the current tenant ID for RLS policy enforcement."""
    await db.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, false)"),
        {"tid": tenant_id},
    )


async def clear_tenant_context(db: AsyncSession):
    """Clear the tenant context."""
    await db.execute(
        text("SELECT set_config('app.current_tenant_id', '', false)"),
    )


@asynccontextmanager
async def tenant_context(db: AsyncSession, tenant_id: str):
    """Context manager that sets tenant_id for RLS policies."""
    await set_tenant_context(db, tenant_id)
    try:
        yield
    finally:
        await clear_tenant_context(db)
