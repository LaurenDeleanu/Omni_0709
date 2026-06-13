import asyncio
import os
import sys
import uuid
import logging
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, text

sys.path.insert(0, os.path.abspath("."))

from app.core.config import settings
from app.models.agent import Agent
from app.services.rag_service import add_document_to_knowledge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_kb")

# The 10 specialized agents and their KB files
AGENTS_DATA = [
    {"name": "HR Copilot", "type": "conversational", "file": "hr_copilot.md"},
    {"name": "Payroll Agent", "type": "conversational", "file": "payroll_agent.md"},
    {"name": "Recruitment Agent", "type": "conversational", "file": "recruitment_agent.md"},
    {"name": "IT Support Agent", "type": "conversational", "file": "it_support_agent.md"},
    {"name": "Training Agent", "type": "conversational", "file": "training_agent.md"},
    {"name": "Compliance Agent", "type": "conversational", "file": "compliance_agent.md"},
    {"name": "Performance Agent", "type": "conversational", "file": "performance_agent.md"},
    {"name": "Onboarding Agent", "type": "conversational", "file": "onboarding_agent.md"},
    {"name": "Sales Agent", "type": "conversational", "file": "sales_agent.md"},
    {"name": "Finance Agent", "type": "conversational", "file": "finance_agent.md"},
]

async def seed_agents_and_kb():
    load_dotenv()
    
    dsn = settings.SQLALCHEMY_DATABASE_URI
    if "postgresql" in dsn and "asyncpg" not in dsn:
        dsn = dsn.replace("postgresql://", "postgresql+asyncpg://")

    logger.info(f"Connecting to database...")
    engine = create_async_engine(dsn, echo=False)

    # Note: SuccessCore uses a multi-tenant schema architecture.
    # For global seeding, we will use the default tenant schema: tenant_acme_corp
    # Ensure schema exists and set it.
    async with engine.begin() as conn:
        try:
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS tenant_acme_corp"))
            await conn.execute(text("SET search_path TO tenant_acme_corp"))
            # Ensure the table is created
            from app.models.agent import Base
            # Using run_sync to create tables in the current schema
            await conn.run_sync(Base.metadata.create_all)
            from app.models.rag import Base as RagBase
            await conn.run_sync(RagBase.metadata.create_all)
        except Exception as e:
            logger.warning(f"Error setting up schema: {e}")

    kb_dir = os.path.join(os.path.dirname(__file__), "knowledge_base")

    async with AsyncSession(engine) as db:
        await db.execute(text("SET search_path TO tenant_acme_corp"))
        
        for agent_info in AGENTS_DATA:
            # Check if agent exists by name
            res = await db.execute(select(Agent).where(Agent.name == agent_info["name"]))
            agent = res.scalar_one_or_none()
            
            if not agent:
                logger.info(f"Creating missing agent: {agent_info['name']}")
                agent = Agent(
                    id=uuid.uuid4().hex,
                    name=agent_info["name"],
                    agent_type=agent_info["type"],
                    ai_model="gpt-4o-mini",
                    ai_system_prompt=f"You are the {agent_info['name']}.",
                    agent_settings={"description": f"Specialized in {agent_info['name']} tasks."}
                )
                db.add(agent)
                await db.flush()
            else:
                logger.info(f"Found existing agent: {agent_info['name']} (ID: {agent.id})")

            # Load the markdown file
            file_path = os.path.join(kb_dir, agent_info["file"])
            if not os.path.exists(file_path):
                logger.error(f"Missing KB file: {file_path}")
                continue
                
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            logger.info(f"Embedding KB for {agent.name}...")
            # Use exponential backoff for OpenAI rate limits
            try:
                # Add document and chunks to knowledge base
                await add_document_to_knowledge(db, agent.id, agent_info["file"], content)
                logger.info(f"Successfully embedded {agent_info['file']} for {agent.name}")
            except Exception as e:
                logger.error(f"Failed to embed {agent_info['file']}: {e}")
                
            # Optional: Sleep to respect rate limits
            await asyncio.sleep(1.0)
            
        await db.commit()
    logger.info("Seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_agents_and_kb())
