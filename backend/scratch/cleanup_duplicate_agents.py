import asyncio, sys
sys.path.insert(0, ".")
from app.core.database import AsyncSessionGlobal
from sqlalchemy import text
from app.models.agent import Agent

async def cleanup():
    invalid_agents = [
        "HR Copilot",
        "IT Helpdesk Assistant",
        "Legal & Compliance Auditor",
        "Sales Navigator Copilot",
        "Code Reviewer Bot",
        "Finance Assistant",
        "Recruitment Screener",
        "Marketing Copywriter",
        "Master Orchestrator"
    ]
    
    async with AsyncSessionGlobal() as db:
        # Get IDs of invalid agents
        result = await db.execute(text("SELECT id FROM agents WHERE name = ANY(:names)"), {"names": invalid_agents})
        invalid_ids = [row[0] for row in result.all()]
        
        if not invalid_ids:
            print("No invalid agents found.")
            return

        print(f"Deleting agents: {invalid_ids}")
        
        # Delete related agent_reputation_scores
        await db.execute(text("DELETE FROM agent_reputation_scores WHERE agent_id = ANY(:ids)"), {"ids": invalid_ids})
        
        # Delete from agent_configs (if any)
        await db.execute(text("DELETE FROM agent_configs WHERE agent_id = ANY(:ids)"), {"ids": invalid_ids})
        
        # Delete from agents
        await db.execute(text("DELETE FROM agents WHERE id = ANY(:ids)"), {"ids": invalid_ids})
        
        await db.commit()
        print("Cleanup complete.")

asyncio.run(cleanup())
