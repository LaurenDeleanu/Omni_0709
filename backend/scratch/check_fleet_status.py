import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.agent_fleet import get_fleet_status
from app.core.database import AsyncSessionGlobal

async def main():
    async with AsyncSessionGlobal() as db:
        status = await get_fleet_status(db)
        for s in status:
            active = "active" if s["active"] and s.get("present_in_db") else "inactive"
            tools = s.get("tools_count", 0)
            runs = s.get("total_runs", 0)
            print(f"  {s['name']}: {active}, runs={runs}, tools={tools}")

asyncio.run(main())
