import asyncio, sys
sys.path.insert(0, ".")
from app.core.database import AsyncSessionGlobal
from app.core.tenant_context import set_tenant_context
from sqlalchemy import select
from app.models.agent import Agent

async def check():
    async with AsyncSessionGlobal() as db:
        # Set tenant context
        await set_tenant_context(db, "tenant_acme_1")
        
        # Query agents
        result = await db.execute(select(Agent))
        agents = result.scalars().all()
        print(f"Agents returned for tenant_acme_1: {len(agents)}")
        for a in agents:
            print(f"- {a.name}")

asyncio.run(check())
