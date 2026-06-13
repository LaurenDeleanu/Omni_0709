import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select, update
from app.models.agent import Agent

async def main():
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as db:
        # Use a specific free model that doesn't require credits
        free_model = 'meta-llama/llama-3.3-70b-instruct:free'
        
        await db.execute(update(Agent).values(ai_model=free_model))
        await db.commit()
        print(f"Updated all agents to use {free_model}")

if __name__ == "__main__":
    asyncio.run(main())
