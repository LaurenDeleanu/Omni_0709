import asyncio, sys
sys.path.insert(0, ".")
from app.core.database import engine
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import delete
from app.models.agent import Agent

async def reset():
    schema = "tenant_acme_corp"
    tenant_engine = engine.execution_options(schema_translate_map={None: schema})
    AsyncSessionTenant = async_sessionmaker(bind=tenant_engine, class_=AsyncSession, autocommit=False, autoflush=False)
    async with AsyncSessionTenant() as db:
        await db.execute(delete(Agent))
        await db.commit()
        print("All agents deleted.")

asyncio.run(reset())
