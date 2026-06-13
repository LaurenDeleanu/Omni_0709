import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.base import Base
from app.models.agent import ConversationEpoch, EpisodicMemory, UserMemoryPreference
from app.core.database import engine


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Memory tables created successfully (or already exist).")


if __name__ == "__main__":
    asyncio.run(main())
