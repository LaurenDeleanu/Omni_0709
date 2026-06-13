"""
Cleanup script: removes duplicate agents by name (case-insensitive).
Keeps the most recently created/updated agent for each name group.
"""
import asyncio
import sys
import os
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.database import AsyncSessionGlobal
from app.models.agent import Agent


async def main():
    async with AsyncSessionGlobal() as db:
        stmt = select(Agent).order_by(Agent.created_at.desc())
        result = await db.execute(stmt)
        all_agents = result.scalars().all()

        groups = defaultdict(list)
        for agent in all_agents:
            groups[agent.name.lower()].append(agent)

        kept = []
        deleted = []

        for name_key, agents in groups.items():
            if len(agents) == 1:
                kept.append(agents[0])
                continue

            agents_sorted = sorted(agents, key=lambda a: a.created_at or a.updated_at, reverse=True)
            keeper = agents_sorted[0]
            dupes = agents_sorted[1:]

            kept.append(keeper)
            for dup in dupes:
                print(f"  DELETE: id={dup.id} name='{dup.name}' type={dup.agent_type} created={dup.created_at}")
                await db.delete(dup)
                deleted.append(dup)

        await db.commit()

        print(f"\n=== CLEANUP RESULTS ===")
        print(f"Total agents before: {len(all_agents)}")
        print(f"Kept: {len(kept)}")
        print(f"Deleted (duplicates): {len(deleted)}")
        print(f"\nAgents remaining:")
        for agent in sorted(kept, key=lambda a: a.name.lower()):
            print(f"  KEPT: id={agent.id} name='{agent.name}' type={agent.agent_type} created={agent.created_at}")


if __name__ == "__main__":
    asyncio.run(main())
