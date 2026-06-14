from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.api.dependencies import get_tenant_db, require_roles, get_current_user
from app.services.ai_service import generate_dynamic_page
from app.services.nlq_service import text_to_sql_query
from app.models.metadata import PageMetadata
from app.schemas.metadata import PageMetadataResponse
from sqlalchemy import select
import uuid
import json
import logging

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

class AIGenerateRequest(BaseModel):
    prompt: str

class AICopilotRequest(BaseModel):
    message: str
    module_context: str = ""
    idempotency_key: str = None


class NLQRequest(BaseModel):
    question: str
    model: str = "gpt-4o-mini"


def _extract_user_payload(current_user: dict) -> dict:
    user_email = current_user.get("email") or ""
    user_name = current_user.get("name") or current_user.get("https://successcore.com/name") or user_email
    user_roles = current_user.get("https://successcore.com/roles", []) or current_user.get("roles", []) or ["employee"]
    tenant_id = current_user.get("https://successcore.com/app_metadata", {}).get("tenant_id", "acme_corp")
    user_department = current_user.get("https://successcore.com/department", "")
    user_id = user_email or current_user.get("sub", "").split("|")[-1]

    return {
        "user_id": user_id,
        "email": user_email,
        "name": user_name,
        "roles": user_roles,
        "role": user_roles[0] if isinstance(user_roles, list) and user_roles else "employee",
        "department": user_department,
        "tenant_id": tenant_id,
        "https://successcore.com/roles": user_roles,
        "https://successcore.com/department": user_department,
        "https://successcore.com/app_metadata": {"tenant_id": tenant_id},
        "https://successcore.com/name": user_name,
    }


@router.post("/query")
async def natural_language_query(
    request: NLQRequest,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(get_current_user),
):
    return await text_to_sql_query(db, request.question, request.model)

@router.post("/generate", response_model=PageMetadataResponse, status_code=status.HTTP_201_CREATED)
async def generate_module_with_ai(
    request: AIGenerateRequest,
    db: AsyncSession = Depends(get_tenant_db)
):
    """
    Toma un prompt del usuario, llama al motor de IA y guarda el módulo generado
    directamente en la base de datos (PageMetadata).
    """
    try:
        ai_result = await generate_dynamic_page(request.prompt)
        
        module_name = ai_result.get("module_name", "ai-generated")
        page_name = ai_result.get("page_name", "page")
        description = ai_result.get("description", "Página generada por IA")
        schema_data = ai_result.get("schema_data", {})

        result = await db.execute(
            select(PageMetadata)
            .where(PageMetadata.module_name == module_name, PageMetadata.page_name == page_name)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.description = description
            existing.schema_data = schema_data
            metadata = existing
        else:
            metadata = PageMetadata(
                id=uuid.uuid4().hex,
                module_name=module_name,
                page_name=page_name,
                description=description,
                schema_data=schema_data
            )
            db.add(metadata)
            
        await db.commit()
        await db.refresh(metadata)
        
        return metadata

    except Exception as e:
        logger.error(f"Error en AI endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _get_or_create_copilot_agent(db: AsyncSession):
    from app.models.agent import Agent, AgentConfig
    from app.services.copilot_prompts import build_copilot_prompt
    from app.services.tool_binding_registry import build_copilot_tool_list
    from app.services.tool_executor import AVAILABLE_TOOLS_SCHEMA

    agent_res = await db.execute(
        select(Agent).where(
            Agent.agent_type == "COPILOT",
            Agent.name == "Platform Copilot"
        ).limit(1)
    )
    agent = agent_res.scalar_one_or_none()
    if not agent:
        # Check by type and pick one without a specific user_id
        agent_res = await db.execute(select(Agent).where(Agent.agent_type == "COPILOT"))
        for a in agent_res.scalars().all():
            if not a.agent_settings or not a.agent_settings.get("copilot_user_id"):
                agent = a
                break

    if not agent:
        system_prompt = await build_copilot_prompt()
        default_tools = await build_copilot_tool_list(["employee"])
        default_tool_schemas = [
            t for t in AVAILABLE_TOOLS_SCHEMA
            if t.get("function", {}).get("name") in default_tools
        ]
        agent = Agent(
            id=uuid.uuid4().hex,
            name="Platform Copilot",
            avatar="\U0001f916",
            agent_type="COPILOT",
            ai_model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
            ai_system_prompt=system_prompt,
            ai_temperature=0.2,
            ai_tone="Profesional y resolutivo",
            agent_settings={
                "ai_tools": json.dumps(
                    [t["function"]["name"] for t in default_tool_schemas]
                )
            },
        )
        db.add(agent)
        await db.flush()
        config = AgentConfig(
            id=uuid.uuid4().hex,
            agent_id=agent.id,
            max_loops=10,
            max_tokens_per_run=50000,
        )
        db.add(config)
        await db.commit()
        await db.refresh(agent)

    return agent


@router.post("/copilot")
@limiter.limit("30/minute")
async def run_platform_copilot(
    request: Request,
    body: AICopilotRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Ejecuta el copiloto de la plataforma con orquestación inteligente:
    - RBAC/ACL dinámico basado en roles del usuario
    - Delegación a especialistas si es necesario
    - Sesiones persistentes con historial
    """
    try:
        from app.services.copilot_orchestrator import detect_delegation_intent, delegate_to_specialist
        from app.services.copilot_session import (
            get_or_create_session,
            save_conversation_turn,
            load_session_as_messages,
        )
        from app.services.agent_runtime import execute_agent_run
        from app.services.copilot_prompts import build_copilot_prompt
        from app.services.tool_binding_registry import build_copilot_tool_list

        user_payload = _extract_user_payload(current_user)
        user_roles = user_payload["roles"]
        user_id = user_payload["user_id"]

        agent = await _get_or_create_copilot_agent(db)
        agent_id = agent.id

        session = await get_or_create_session(user_id, agent_id, db)
        history_messages = await load_session_as_messages(session.id, 20, db)

        # Query platform knowledge based on the user's message
        platform_knowledge = ""
        try:
            from app.services.platform_knowledge import query_platform_knowledge
            platform_knowledge = await query_platform_knowledge(body.message, db, limit=3)
        except Exception as pk_err:
            logger.warning(f"Platform knowledge query failed: {pk_err}")

        # Determine language (locale)
        accept_language = request.headers.get("Accept-Language", "")
        language = "en" if "en" in accept_language.lower() else "es"
        if current_user.get("locale") == "en" or current_user.get("language") == "en":
            language = "en"

        enhanced_system_prompt = await build_copilot_prompt(
            module_context=body.module_context or "",
            user_role=user_payload["role"],
            platform_knowledge=platform_knowledge,
            language=language,
        )

        try:
            from app.services.semantic_memory import retrieve_context_for_query as _retrieve_context
            memory_context = await _retrieve_context(body.message, user_id, db, max_memories=3)
            if memory_context:
                enhanced_system_prompt = f"{enhanced_system_prompt}\n\n[USER MEMORY CONTEXT]\n{memory_context}\n"
        except Exception as mem_err:
            logger.warning(f"Memory context retrieval failed: {mem_err}")

        agent.ai_system_prompt = enhanced_system_prompt
        await db.commit()

        # Set scoped tools based on user roles
        agent.agent_settings = agent.agent_settings or {}
        scoped_tools = await build_copilot_tool_list(user_roles)
        agent.agent_settings["ai_tools"] = json.dumps(scoped_tools)
        await db.commit()

        user_email = user_payload["email"]
        user_name = user_payload["name"]
        user_department = user_payload["department"]

        user_context = (
            f"[CONTEXTO DEL USUARIO]\n"
            f"Usuario actual: {user_name} ({user_email})\n"
            f"Rol: {', '.join(user_roles) if isinstance(user_roles, list) else user_roles}\n"
            f"Departamento: {user_department}\n"
            f"Usa su email ({user_email}) como identificador por defecto.\n"
        )

        if body.module_context:
            user_context += f"\n[MÓDULO ACTUAL]\n{body.module_context}\n"

        input_payload = {
            "message": f"{user_context}\n\n[SOLICITUD]\n{body.message}",
            "user_id": user_id,
        }

        # Detect if this query should be delegated to a specialist agent
        delegation = await detect_delegation_intent(body.message, db)

        response_text = ""
        delegated_to = None

        if delegation["should_delegate"] and delegation["confidence"] > 0.7:
            agent_type = delegation["agent_type"]
            specialist_result = await delegate_to_specialist(body.message, agent_type, user_id, db)
            response_text = specialist_result.get("reply", "")
            delegated_to = agent_type
            if not response_text:
                response_text = (
                    f"Lo siento, no pude delegar esta consulta al especialista {agent_type}. "
                    f"Error: {specialist_result.get('error', 'desconocido')}"
                )
        else:
            result = await execute_agent_run(db, agent_id, input_payload, trigger_source="manual")
            response_text = result.get("reply", "")

        await save_conversation_turn(session.id, "user", body.message, db)
        await save_conversation_turn(session.id, "assistant", response_text, db)

        return {
            "success": True,
            "response": response_text,
            "session_id": session.id,
            "delegated_to": delegated_to,
            "delegation_reason": delegation.get("reason") if delegated_to else None,
            "confidence": delegation.get("confidence") if delegated_to else None,
        }

    except Exception as e:
        logger.error(f"Error ejecutando Copiloto de Plataforma: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/copilot/stream")
@limiter.limit("30/minute")
async def stream_platform_copilot(
    request: Request,
    body: AICopilotRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        import json
        from app.services.agent_runtime import execute_agent_run_streaming
        from app.services.copilot_session import get_or_create_session, save_conversation_turn
        from app.services.copilot_orchestrator import detect_delegation_intent, delegate_to_specialist
        from app.services.copilot_prompts import build_copilot_prompt
        from app.services.tool_binding_registry import build_copilot_tool_list
        from app.models.agent import Agent

        user_payload = _extract_user_payload(current_user)
        user_id = user_payload["user_id"]
        user_name = user_payload["name"]
        user_email = user_payload["email"]
        user_roles = user_payload["roles"]

        agent = await _get_or_create_copilot_agent(db)
        session = await get_or_create_session(user_id, agent.id, db)
        await save_conversation_turn(session.id, "user", body.message, db)

        # Detect delegation in streaming
        delegation = await detect_delegation_intent(body.message, db)
        streaming_agent_id = agent.id
        delegated_to = None

        if delegation["should_delegate"] and delegation["confidence"] > 0.7:
            agent_type = delegation["agent_type"]
            agent_res = await db.execute(
                select(Agent).where(
                    Agent.agent_type == agent_type.upper(),
                    Agent.is_active == True,
                )
            )
            specialist = agent_res.scalars().first()
            if not specialist:
                agent_res = await db.execute(select(Agent).where(Agent.agent_type == agent_type.upper()).limit(1))
                specialist = agent_res.scalars().first()
            if specialist:
                streaming_agent_id = specialist.id
                delegated_to = agent_type

        # Query platform knowledge based on the user's message
        platform_knowledge = ""
        try:
            from app.services.platform_knowledge import query_platform_knowledge
            platform_knowledge = await query_platform_knowledge(body.message, db, limit=3)
        except Exception as pk_err:
            logger.warning(f"Platform knowledge query failed (stream): {pk_err}")

        # Determine language (locale)
        accept_language = request.headers.get("Accept-Language", "")
        language = "en" if "en" in accept_language.lower() else "es"
        if current_user.get("locale") == "en" or current_user.get("language") == "en":
            language = "en"

        enhanced_system_prompt = await build_copilot_prompt(
            module_context=body.module_context or "",
            user_role=user_payload["role"],
            platform_knowledge=platform_knowledge,
            language=language,
        )

        try:
            from app.services.semantic_memory import retrieve_context_for_query as _retrieve_context
            memory_context = await _retrieve_context(body.message, user_id, db, max_memories=3)
            if memory_context:
                enhanced_system_prompt = f"{enhanced_system_prompt}\n\n[USER MEMORY CONTEXT]\n{memory_context}\n"
        except Exception as mem_err:
            logger.warning(f"Memory context retrieval failed (stream): {mem_err}")

        # If streaming via Copilot, update its prompt/tools
        if streaming_agent_id == agent.id:
            agent.ai_system_prompt = enhanced_system_prompt
            await db.commit()

            scoped_tools = await build_copilot_tool_list(user_roles)
            agent.agent_settings = agent.agent_settings or {}
            agent.agent_settings["ai_tools"] = json.dumps(scoped_tools)
            await db.commit()

        user_context = (
            f"[CONTEXTO DEL USUARIO]\n"
            f"Usuario actual: {user_name} ({user_email})\n"
            f"Rol: {', '.join(user_roles) if isinstance(user_roles, list) else user_roles}\n"
            f"Departamento: {user_payload.get('department', '')}\n"
            f"Usa su email ({user_email}) como identificador por defecto.\n"
        )

        if body.module_context:
            user_context += f"\n[MÓDULO ACTUAL]\n{body.module_context}\n"

        input_payload = {
            "message": f"{user_context}\n\n[SOLICITUD]\n{body.message}",
            "user_id": user_id,
        }

        async def generate():
            full_response = []
            async for event in execute_agent_run_streaming(db, streaming_agent_id, input_payload, trigger_source="manual"):
                yield f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
                if event.get("event") == "delta" and event.get("data", {}).get("content"):
                    full_response.append(event["data"]["content"])
                elif event.get("event") == "token" and event.get("data"):
                    data_obj = event.get("data")
                    if isinstance(data_obj, dict) and "text" in data_obj:
                        full_response.append(data_obj["text"])
                    elif isinstance(data_obj, str):
                        full_response.append(data_obj)
            if full_response:
                await save_conversation_turn(session.id, "assistant", "".join(full_response), db)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )
    except Exception as e:
        logger.error(f"Error en copiloto streaming: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Session API endpoints ---
@router.get("/copilot/sessions")
async def list_copilot_sessions(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """List all copilot sessions for the current user."""
    from app.services.copilot_session import list_user_sessions

    user_payload = _extract_user_payload(current_user)
    sessions = await list_user_sessions(user_payload["user_id"], db)
    return {"success": True, "sessions": sessions}


@router.post("/copilot/sessions/{session_id}/end")
async def end_copilot_session(
    session_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """End a copilot session."""
    from app.services.copilot_session import end_session

    result = await end_session(session_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    try:
        from app.services.semantic_memory import auto_extract_milestones
        await auto_extract_milestones(session_id, db)
    except Exception as e:
        logger.warning(f"Milestone extraction for session {session_id} failed: {e}")

    return {"success": True, "session": result}


@router.get("/copilot/sessions/{session_id}")
async def get_copilot_session(
    session_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Get the history of a copilot session."""
    from app.services.copilot_session import get_session_history

    history = await get_session_history(session_id, 50, db)
    return {"success": True, "session_id": session_id, "turns": len(history), "history": history}
