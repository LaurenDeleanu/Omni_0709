import asyncio, sys
sys.path.insert(0, ".")
from app.core.database import AsyncSessionGlobal
from sqlalchemy import select, func
from app.models.agent import Agent

async def count():
    async with AsyncSessionGlobal() as db:
        cnt = await db.scalar(select(func.count(Agent.id)))
        print(f"Total agents in DB: {cnt}")
        
        result = await db.execute(select(Agent.name, Agent.is_active))
        for r in result.all():
            print(f"- {r[0]} (Active: {r[1]})")

asyncio.run(count())
