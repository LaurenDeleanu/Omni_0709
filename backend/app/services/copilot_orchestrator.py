import logging
import json
import time
import uuid
from typing import Any, Optional
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent import Agent, AgentConfig, AgentExecutionRun
from app.services.llm_router import get_llm_client
from app.services.agent_runtime import execute_agent_run
from app.services.tool_acl import build_copilot_tool_list, get_allowed_tools_for_roles
from app.services.tool_executor import AVAILABLE_TOOLS_SCHEMA

logger = logging.getLogger(__name__)

SPECIALIST_AGENT_TYPES = [
    "hr_assistant",
    "payroll_specialist",
    "it_helpdesk",
    "recruiter",
    "sales_coach",
    "performance_coach",
    "onboarding_buddy",
    "compliance_officer",
    "data_analyst",
    "finance_manager",
]

SPECIALIST_CAPABILITIES = {
    "hr_assistant": "Handles HR queries: employee profiles, department info, vacation balances, time off requests, org charts, team members, OKRs, performance reviews.",
    "payroll_specialist": "Handles payroll: payslips, tax rules, payroll cycles, compensation changes, bonuses, financial ledger queries, expense summaries.",
    "it_helpdesk": "Handles IT support: ticket creation, asset management, ticket resolution, knowledge base search, IT ticket statistics, auto-tagging.",
    "recruiter": "Handles recruitment: job postings, candidate management, interview scheduling, pipeline stats, resume parsing, candidate screening, offer letters.",
    "sales_coach": "Handles CRM/sales: pipeline overview, client details, deal stats, lead activity, task creation for leads.",
    "performance_coach": "Handles performance management: OKRs, key results, reviews, team OKRs, kudos, training progress, course recommendations.",
    "onboarding_buddy": "Handles onboarding: new hire setup, onboarding plans, training enrollment, course catalog, buddy assignments.",
    "compliance_officer": "Handles compliance: contracts, compliance status, whistleblower reports, audit reports, regulatory checks.",
    "data_analyst": "Handles data analysis: department stats, pipeline stats, ticket stats, deal stats, trend analysis, forecasting.",
    "finance_manager": "Handles finance: financial ledger, expense summaries, budget tracking, financial reports, contract financials.",
}

DELEGATION_CLASSIFICATION_PROMPT = """
You are a delegation classifier. Analyze the user request.
We have the following agents: {agent_types}
With the following capabilities: {capabilities}

Decide if we should delegate the task.
Output a JSON object with:
- should_delegate (true/false)
- agent_type (one of the agent types, or null)
- confidence (0.0 to 1.0)
"""


@dataclass
class CopilotResponse:
    response: str
    delegated: bool = False
    delegated_to: str = ""
    delegation_reason: str = ""
    tools_used: list = field(default_factory=list)
    knowledge_sources: list = field(default_factory=list)


async def _query_platform_knowledge(user_message: str, db: AsyncSession) -> list[str]:
    try:
        from app.services.rag_service import query_knowledge_base
        chunks = await query_knowledge_base(db, None, user_message, limit=3)
        return [c.get("content", "") for c in chunks]
    except Exception as e:
        logger.warning(f"Platform knowledge query failed: {e}")
        return []


async def detect_delegation_intent(user_message: str, db: AsyncSession) -> dict:
    """Smart delegation detection with keyword pre-filter + LLM fallback."""
    from app.services.delegation_classifier import detect_delegation_intent_smart
    return await detect_delegation_intent_smart(user_message, db)


async def delegate_to_specialist(
    user_message: str,
    agent_type: str,
    user_id: str,
    db: AsyncSession,
) -> dict:
    try:
        agent_res = await db.execute(
            select(Agent).where(
                Agent.agent_type == agent_type.upper(),
                Agent.is_active == True,
            )
        )
        agent = agent_res.scalars().first() if hasattr(agent_res, "scalars") else None
        if not agent:
            agent_res = await db.execute(select(Agent).where(Agent.agent_type == agent_type.upper()))
            agent = agent_res.scalars().first() if hasattr(agent_res, "scalars") else None

        if not agent:
            return {
                "reply": f"No hay un agente especialista '{agent_type}' configurado. Usa /settings/agents para crear uno.",
                "status": "error",
                "error": "agent_not_found",
            }

        input_payload = {
            "message": user_message,
            "user_id": user_id,
        }

        result = await execute_agent_run(db, agent.id, input_payload, trigger_source="delegation")
        return result
    except Exception as e:
        logger.error(f"Specialist delegation failed: {e}")
        return {
            "reply": f"Error delegando al especialista {agent_type}: {str(e)}",
            "status": "error",
            "error": str(e),
        }


async def copilot_orchestrate(
    user_message: str,
    user_payload: dict,
    module_context: str,
    db: AsyncSession,
) -> CopilotResponse:
    knowledge_sources = await _query_platform_knowledge(user_message, db)

    delegation = await detect_delegation_intent(user_message, db)

    if delegation["should_delegate"] and delegation["confidence"] > 0.7:
        agent_type = delegation["agent_type"]
        logger.info(
            f"Copilot delegating to specialist: {agent_type} "
            f"(confidence={delegation['confidence']:.2f})"
        )

        specialist_result = await delegate_to_specialist(
            user_message, agent_type, user_payload.get("user_id", ""), db
        )

        response_text = specialist_result.get("reply", "")
        if specialist_result.get("status") == "error" or not response_text:
            logger.warning(f"Delegation failed: {specialist_result.get('error', 'desconocido')}. Falling back to Copilot.")
            delegation["should_delegate"] = False  # Fallback to normal copilot execution
        else:
            return CopilotResponse(
                response=response_text,
                delegated=True,
                delegated_to=agent_type,
                delegation_reason=delegation.get("reason", "High confidence delegation"),
                knowledge_sources=knowledge_sources,
            )

    user_roles = user_payload.get("https://successcore.com/roles", []) or user_payload.get("roles", []) or ["employee"]
    scoped_tools = build_copilot_tool_list(user_roles, AVAILABLE_TOOLS_SCHEMA)

    from app.services.agent_fleet import _get_or_create_copilot_agent
    
    user_id_str = user_payload.get("user_id", "default_copilot_user")
    agent = await _get_or_create_copilot_agent("COPILOT", user_id_str, db)
    
    # Update scoped tools dynamically based on user role
    agent.agent_settings = agent.agent_settings or {}
    agent.agent_settings["ai_tools"] = json.dumps(
        [t["function"]["name"] for t in scoped_tools]
    )
    # The copilot also gets access to its extended tools from the fleet
    await db.commit()
    agent_id = agent.id

    import datetime
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tenant_lang = user_payload.get("language", "es") # default to Spanish if not specified

    user_context = (
        f"[CONTEXTO DEL USUARIO]\n"
        f"Usuario actual: {user_payload.get('name', '')} ({user_payload.get('email', '')})\n"
        f"Rol: {', '.join(user_roles) if isinstance(user_roles, list) else user_roles}\n"
        f"Departamento: {user_payload.get('https://successcore.com/department', '')}\n"
        f"Tenant: {user_payload.get('tenant_id', 'acme_corp')}\n"
        f"Idioma Preferido (Tenant Language): {tenant_lang}\n"
        f"Fecha y Hora Actual: {current_time}\n"
        f"Reglas: Actua siempre como si fueras este usuario. Solo puedes hacer lo que sus roles te permiten.\n"
        f"Idioma de Respuesta: RESPONDE ESTRICTAMENTE EN EL IDIOMA PREFERIDO DEL USUARIO ({tenant_lang}).\n"
    )

    if module_context:
        user_context += f"\n[MÓDULO ACTUAL]\n{module_context}\n"

    if knowledge_sources:
        knowledge_text = "\n".join(f"- {s}" for s in knowledge_sources)
        user_context += f"\n[CONOCIMIENTO DE PLATAFORMA]\n{knowledge_text}\n"

    input_payload = {
        "message": f"{user_context}\n\n[SOLICITUD DEL USUARIO]\n{user_message}",
        "user_id": user_payload.get("user_id", ""),
    }

    result = await execute_agent_run(db, agent_id, input_payload, trigger_source="manual")

    tools_used = []
    if result.get("trace"):
        try:
            trace = json.loads(result["trace"]) if isinstance(result["trace"], str) else result["trace"]
            for step in trace:
                if isinstance(step, dict) and step.get("step") == "tool_call":
                    tools_used.append(step.get("tool", ""))
        except (json.JSONDecodeError, TypeError):
            pass

    return CopilotResponse(
        response=result.get("reply", ""),
        delegated=False,
        tools_used=tools_used,
        knowledge_sources=knowledge_sources,
    )
