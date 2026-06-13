import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger("successcore.residency")

TENANT_DB_MAP = {
    "EU": "postgresql+asyncpg://db-eu.internal:5432/successcore",
    "US": "postgresql+asyncpg://db-us.internal:5432/successcore",
}


def get_tenant_db_url(tenant_id: str, residency: str = "EU") -> str:
    default_url = TENANT_DB_MAP.get(residency.upper(), TENANT_DB_MAP["EU"])
    return default_url


async def get_tenant_residency(db: AsyncSession, tenant_id: str) -> str:
    from app.models.tenant import Tenant
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant and hasattr(tenant, 'data_residency') and tenant.data_residency:
        return tenant.data_residency
    return "EU"
