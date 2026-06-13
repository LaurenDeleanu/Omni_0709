import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agent import Agent
from app.services.guard_service import detect_injection
from app.services.agent_memory import load_conversation_memory
from app.services.rag_service import query_knowledge_base
from app.services.shared_context_bus import find_reusable_context

logger = logging.getLogger("successcore.agent_context_builder")

async def build_agent_context(
    db: AsyncSession,
    agent: Agent,
    input_payload: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], Optional[List[Dict[str, Any]]], str, str, str, List[Dict[str, Any]]]:
    """
    Assembles user message context, conversation history, RAG documents, and active tool schemas.
    """
    user_msg = input_payload.get("message", "")
    user_id = input_payload.get("user_id", "")
    tenant = input_payload.get("tenant_id", "default")
    trace_steps = []
    
    # 1. Message Security check
    is_injection, reason = detect_injection(user_msg)
    if is_injection:
        raise ValueError(f"Message blocked by security guard: {reason}")
        
    # 2. Conversation memory loading
    memory_turns = await load_conversation_memory(db, agent.id, user_id, max_turns=10)
    
    # 3. RAG retrieval
    rag_context = ""
    if user_msg:
        rag_chunks = await query_knowledge_base(db, agent.id, user_msg, limit=3)
        if rag_chunks:
            context_str = "\n".join([f"- Fragmento: {c['content']}" for c in rag_chunks])
            rag_context = f"\n\n[Base de Conocimiento Recuperada]:\n{context_str}"
            trace_steps.append({"step": "rag_retrieval", "details": f"Recuperados {len(rag_chunks)} fragmentos del RAG."})

    # 3.5. Shared Knowledge Bus retrieval
    shared_context = ""
    if user_msg:
        try:
            shared_facts = await find_reusable_context(tenant_id=tenant, query=user_msg, db=db, limit=3)
            matches = shared_facts.get("matches", [])
            if matches:
                facts_str = "\n".join([f"- [Topic: {m['topic']}] {json.dumps(m['data'])}" for m in matches])
                shared_context = f"\n\n[Conocimiento Compartido por otros Agentes]:\n{facts_str}"
                trace_steps.append({"step": "shared_context_bus", "details": f"Found {len(matches)} shared facts."})
        except Exception as e:
            logger.debug(f"Shared context retrieval skipped: {e}")

    # 4. System prompt assembly
    messages = []
    for mem_turn in memory_turns:
        messages.append(mem_turn)

    import datetime
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    system_prompt = (
        f"[Identidad del Agente]\nEres el agente {agent.name} (Tipo: {agent.agent_type}).\n\n"
        f"[Contexto Temporal]\nFecha y Hora Actual: {current_time}\n\n"
        f"{agent.ai_system_prompt}"
    )

    if rag_context:
        system_prompt += rag_context
    if shared_context:
        system_prompt += shared_context
    if agent.ai_guardrails:
        system_prompt += f"\n\n[Reglas de Seguridad y Límites]:\n{agent.ai_guardrails}"
    if agent.ai_tone:
        system_prompt += f"\n\nPor favor, responde manteniendo un tono: {agent.ai_tone}"

    system_prompt += (
        f"\n\n[Instrucciones de Herramientas]\nSi tienes herramientas disponibles, úsalas proactivamente para resolver la consulta. No pidas permiso para usar herramientas, simplemente invócalas."
        f"\n\n[Instrucciones de Formato de Datos]\nUsa Markdown para darle formato a tu respuesta. Presenta listas, tablas de datos y pasos de manera estructurada y profesional."
    )
        
    messages.append({"role": "system", "content": system_prompt})
    if user_msg:
        messages.append({"role": "user", "content": user_msg})

    # 5. Parse active tools — unified resolution through registry + aliases
    active_tools = None
    settings_tools = agent.agent_settings.get("ai_tools") if agent.agent_settings else None
    if settings_tools:
        try:
            if isinstance(settings_tools, str):
                tool_names = json.loads(settings_tools)
            else:
                tool_names = settings_tools
            if isinstance(tool_names, list) and tool_names:
                from app.services.tool_registry import get_tools_for_agent
                active_tools = get_tools_for_agent(tool_names)
                if active_tools:
                    logger.info(f"Resolved {len(active_tools)}/{len(tool_names)} tools for agent {agent.name}")
                else:
                    logger.warning(f"No tools resolved for agent {agent.name} from list: {tool_names[:5]}...")
        except Exception as e:
            logger.warning(f"Error parsing ai_tools for agent {agent.name}: {e}")

    return messages, active_tools, user_msg, user_id, tenant, trace_steps

