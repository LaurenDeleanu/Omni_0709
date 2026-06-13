"""
Seed script to build the platform knowledge index.
Calls build_platform_knowledge_index() to populate the RAG documents
for the copilot's platform knowledge base.

Usage:
    cd backend
    python scratch/build_knowledge_index.py
"""

import asyncio
import sys
import os

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import AsyncSessionGlobal
from app.services.platform_knowledge import build_platform_knowledge_index, PLATFORM_KNOWLEDGE_DOCUMENTS


async def main():
    async with AsyncSessionGlobal() as db:
        result = await build_platform_knowledge_index(db)
        print(f"Knowledge index built: {result}")
        print(f"Total platform knowledge modules available: {len(PLATFORM_KNOWLEDGE_DOCUMENTS)}")


if __name__ == "__main__":
    asyncio.run(main())
