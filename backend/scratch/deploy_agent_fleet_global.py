import asyncio, sys
sys.path.insert(0, ".")
from app.core.database import engine, AsyncSessionGlobal
from app.services.agent_fleet import deploy_agent_fleet

async def deploy():
    async with AsyncSessionGlobal() as db:
        result = await deploy_agent_fleet(db)
        print(f"Created: {len(result['created'])} | Updated: {len(result['updated'])}")
        for a in result["created"] + result["updated"]:
            print(f"  - {a}")

asyncio.run(deploy())
