import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.agent_fleet import deploy_agent_fleet
from app.core.database import AsyncSessionGlobal


async def deploy():
    async with AsyncSessionGlobal() as db:
        result = await deploy_agent_fleet(db)
        print(f"Created: {len(result['created'])} agents")
        print(f"Updated: {len(result['updated'])} agents")
        print(f"Skipped: {len(result['skipped'])} agents")
        print()
        for agent in result["created"]:
            print(f"  + CREATED: {agent}")
        for agent in result["updated"]:
            print(f"  ~ UPDATED: {agent}")
        for agent in result["skipped"]:
            print(f"  = SKIPPED: {agent}")


if __name__ == "__main__":
    asyncio.run(deploy())
