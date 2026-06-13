import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix Unicode printing on Windows console
sys.stdout.reconfigure(encoding='utf-8')

# Force mock LLM endpoint for verification testing
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-32chars"

from app.core.database import engine
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select
from app.models.agent import Agent
from app.services.copilot_orchestrator import copilot_orchestrate
from app.services.omni_orchestrator import OmniOrchestrator
from app.services.agent_runtime import execute_agent_run

async def run_scenario_1(db: AsyncSession):
    print("\n=== Scenario 1: Bilingual Direct Copilot Queries ===")
    user_payload_es = {
        "user_id": "test_user_es",
        "email": "test_es@successcore.com",
        "name": "Juan Pérez",
        "roles": ["employee"],
        "department": "Engineering",
        "tenant_id": "acme_corp"
    }
    
    # Query in Spanish
    print("Sending message in Spanish: 'Hola, ¿quién eres y qué puedes hacer?'")
    result_es = await copilot_orchestrate(
        user_message="Hola, ¿quién eres y qué puedes hacer?",
        user_payload=user_payload_es,
        module_context="hr",
        db=db
    )
    print(f"Response (Spanish): {result_es.response[:200]}...")
    print(f"Delegated: {result_es.delegated}")
    
    # Query in English
    print("\nSending message in English: 'Hello, who are you and what can you do?'")
    user_payload_en = user_payload_es.copy()
    user_payload_en["locale"] = "en"
    
    result_en = await copilot_orchestrate(
        user_message="Hello, who are you and what can you do?",
        user_payload=user_payload_en,
        module_context="hr",
        db=db
    )
    print(f"Response (English): {result_en.response[:200]}...")
    print(f"Delegated: {result_en.delegated}")


async def run_scenario_2(db: AsyncSession):
    print("\n=== Scenario 2: Delegation to PAYROLL_SPECIALIST ===")
    user_payload = {
        "user_id": "test_user_payroll",
        "email": "test_payroll@successcore.com",
        "name": "María Gómez",
        "roles": ["employee"],
        "department": "Engineering",
        "tenant_id": "acme_corp"
    }
    
    message = "Muestra mi nómina del mes pasado"
    print(f"Sending message: '{message}'")
    
    result = await copilot_orchestrate(
        user_message=message,
        user_payload=user_payload,
        module_context="",
        db=db
    )
    print(f"Response: {result.response[:200]}...")
    print(f"Delegated: {result.delegated}")
    print(f"Delegated To: {result.delegated_to}")
    print(f"Delegation Reason: {result.delegation_reason}")


async def run_scenario_3(db: AsyncSession):
    print("\n=== Scenario 3: Omni Orchestrator Decomposition & Execution ===")
    
    query = "Muéstrame el headcount del departamento de ingeniería y sus próximas vacaciones aprobadas"
    print(f"Decomposing query: '{query}'")
    
    # We find the Omni agent in the db
    agent_res = await db.execute(select(Agent).where(Agent.agent_type == "OMNI_MASTER"))
    omni_agent = agent_res.scalars().first()
    
    if not omni_agent:
        print("Omni Master agent not found in database!")
        return
        
    user_id = "test_user_omni"
    
    # Run the OmniOrchestrator directly
    orchestrator = OmniOrchestrator(
        db=db,
        omni_agent=omni_agent,
        user_message=query,
        user_id=user_id,
        mode="hierarchical"
    )
    result = await orchestrator.run_orchestration()
    
    # Let's read final synthesized response
    final_answer = getattr(result, "final_answer", "")
    sub_results = getattr(result, "sub_results", [])
    token_usage = getattr(result, "total_tokens_used", 0)
    cost_usd = getattr(result, "total_cost_usd", 0.0)
    
    def safe_print(text):
        try:
            print(text)
        except UnicodeEncodeError:
            print(text.encode('ascii', 'replace').decode('ascii'))
            
    safe_print("\nDecomposition Plan/Sub Results:")
    for sub in sub_results:
        safe_print(f"  - Sub-task agent type: {sub.agent_type}, Status: {sub.status}")
        safe_print(f"    Result snippet: {sub.result[:150]}...")
            
    safe_print(f"\nFinal synthesized response: {final_answer[:300]}...")
    safe_print(f"Token usage: {token_usage}, Cost USD: {cost_usd}")


async def main():
    schema = "tenant_acme_corp"
    tenant_engine = engine.execution_options(schema_translate_map={None: schema})
    AsyncSessionTenant = async_sessionmaker(
        bind=tenant_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False  # Crucial to match actual server and prevent lazy-load/MissingGreenlet
    )
    
    async with AsyncSessionTenant() as db:
        await run_scenario_1(db)
        await run_scenario_2(db)
        await run_scenario_3(db)

if __name__ == "__main__":
    asyncio.run(main())
