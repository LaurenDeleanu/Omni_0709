import asyncio
import sys
import os
sys.path.insert(0, ".")

from app.core.database import AsyncSessionGlobal
from app.core.tenant_context import set_tenant_context
from sqlalchemy import select
from app.models.agent import Agent
from app.services.rag_service import add_document_to_knowledge

FILE_TO_AGENT_MAP = {
    "hr_copilot.md": ["HR Assistant Pro"],
    "payroll_agent.md": ["Payroll Specialist"],
    "it_support_agent.md": ["IT Helpdesk"],
    "recruitment_agent.md": ["Recruiter Pro"],
    "sales_agent.md": ["Sales Coach & CRM Manager"],
    "performance_agent.md": ["Performance Coach"],
    "onboarding_agent.md": ["Onboarding Buddy"],
    "compliance_agent.md": ["Compliance Officer"],
    "finance_agent.md": ["Finance Manager"],
    "training_agent.md": ["Onboarding Buddy", "HR Assistant Pro"], # Fallback since Training Agent doesn't exist
    "global_core_context.md": ["Omni Master Pro", "Platform Copilot", "Data Analyst"]
}

async def seed_rag():
    kb_dir = "knowledge_base"
    
    async with AsyncSessionGlobal() as db:
        await set_tenant_context(db, "tenant_acme_1")
        
        # Load all agents
        result = await db.execute(select(Agent))
        agents = result.scalars().all()
        agent_dict = {a.name: a for a in agents}
        
        print(f"Found {len(agents)} agents in database.")
        
        for filename, agent_names in FILE_TO_AGENT_MAP.items():
            filepath = os.path.join(kb_dir, filename)
            if not os.path.exists(filepath):
                print(f"File not found: {filepath}")
                continue
                
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            for agent_name in agent_names:
                agent = agent_dict.get(agent_name)
                if not agent:
                    print(f"Warning: Agent '{agent_name}' not found for file {filename}")
                    continue
                    
                print(f"Ingesting {filename} for agent {agent.name}...")
                try:
                    doc = await add_document_to_knowledge(
                        db=db,
                        agent_id=agent.id,
                        filename=filename,
                        content=content
                    )
                    print(f"  -> Success! Created doc {doc.id}")
                except Exception as e:
                    print(f"  -> Error: {e}")

if __name__ == "__main__":
    asyncio.run(seed_rag())
