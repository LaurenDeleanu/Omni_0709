from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, Response, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import json
import uuid

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.dependencies import get_tenant_db, require_roles, get_current_user
from app.api.v1._pagination import paginate_query
from app.schemas.pagination import PaginatedResponse
from app.models.agent import Agent, AgentConfig, AgentExecutionRun, BenchmarkRun
from app.models.rag import KnowledgeDocument
from app.services.agent_runtime import execute_agent_run, execute_agent_run_streaming
from app.services.rag_service import add_document_to_knowledge
from app.services.file_parser import parse_file_content
from app.services.llm_router import encrypt_key
from app.services.prompt_versioning import get_prompt_store
from app.services.tool_registry import generate_tool_scaffold
from app.services.skill_packaging import import_agent_package, export_agent_package
from app.services.agent_marketplace import get_marketplace_agents
from app.services.cron_triggers import schedule_agent_trigger, list_scheduled_triggers, remove_scheduled_trigger
from app.services.prompt_templates import get_templates, get_template_by_id

from app.api.v1.agent_schedules import router as schedules_router
from app.api.v1.agent_triggers import router as triggers_router
from app.api.v1.agent_budgets import router as budgets_router

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()
router.include_router(schedules_router, prefix="/schedules", tags=["Agent Schedules"])
router.include_router(triggers_router, prefix="/triggers", tags=["Agent Triggers"])
router.include_router(budgets_router, prefix="/budgets", tags=["Agent Budgets"])

# --- Pydantic Schemas ---
class AgentConfigSchema(BaseModel):
    max_loops: int = 10
    max_tokens_per_run: int = 50000
    input_schema: dict = {}
    output_schema: dict = {}

class AgentCreate(BaseModel):
    name: str
    avatar: Optional[str] = None
    agentType: Optional[str] = None
    aiModel: Optional[str] = None
    aiSystemPrompt: Optional[str] = None
    aiTemperature: Optional[float] = None
    aiTone: Optional[str] = None
    aiGuardrails: Optional[str] = None
    aiTools: Optional[str] = None
    aiFallbackModels: Optional[str] = None
    aiKnowledgeBase: Optional[str] = None
    aiVisionModel: Optional[str] = None
    agentSettings: Optional[dict] = None
    workflow_graph: Optional[dict] = None
    config: Optional[AgentConfigSchema] = None

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    agentType: Optional[str] = None
    aiModel: Optional[str] = None
    aiSystemPrompt: Optional[str] = None
    aiTemperature: Optional[float] = None
    aiTone: Optional[str] = None
    aiGuardrails: Optional[str] = None
    aiTools: Optional[str] = None
    aiFallbackModels: Optional[str] = None
    aiKnowledgeBase: Optional[str] = None
    aiVisionModel: Optional[str] = None
    agentSettings: Optional[dict] = None
    is_active: Optional[bool] = None
    workflow_graph: Optional[dict] = None
    config: Optional[AgentConfigSchema] = None

class ChatRequest(BaseModel):
    message: str
    collected_data: Optional[dict] = None

class RAGDocumentCreate(BaseModel):
    filename: str
    content: str

class CrewTaskRequest(BaseModel):
    task: str
    agent_ids: Optional[list[str]] = None
    max_parallel: int = 3
    worker_timeout_seconds: int = 120

class SwarmRunRequest(BaseModel):
    task: str
    starting_agent_id: Optional[str] = None
    agent_ids: Optional[list[str]] = None
    max_handoffs: int = 5

# --- Routes ---

@router.get("")
async def list_agents(
    page: Optional[int] = Query(None, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    stmt = select(Agent).order_by(Agent.created_at.desc())

    if page is not None:
        result = await paginate_query(db, stmt, page=page, page_size=page_size)
        agent_list = [_agent_to_dict(a) for a in result["items"]]
    else:
        agents = (await db.execute(stmt)).scalars().all()
        agent_list = [_agent_to_dict(a) for a in agents]

    seen_names: set = set()
    deduped: list = []
    for a in agent_list:
        key = a["name"].lower()
        if key not in seen_names:
            seen_names.add(key)
            deduped.append(a)

    if page is not None:
        return PaginatedResponse(items=deduped, total=len(deduped), page=result["page"], page_size=result["page_size"], total_pages=result["total_pages"])
    return deduped


def _agent_to_dict(a: Agent) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "avatar": a.avatar,
        "agentType": a.agent_type.upper() if a.agent_type else "CONVERSATIONAL",
        "agent_type": a.agent_type.upper() if a.agent_type else "CONVERSATIONAL",
        "aiModel": a.ai_model,
        "is_active": a.is_active,
        "created_at": a.created_at.isoformat() if a.created_at else None
    }


@router.get("/tool-suggestions")
async def suggest_agent_tools(description: str = Query(""), purpose: str = Query(""), _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))):
    from app.services.tool_suggest import suggest_tools
    return {"suggested": suggest_tools(description, purpose)}


@router.get("/models")
async def list_available_models(
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Obtiene la lista dinámica de modelos disponibles, incluyendo OpenAI, Gemini y OpenRouter.
    """
    try:
        from app.services.llm_router import get_dynamic_models
        models = await get_dynamic_models()
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Crea un nuevo agente de IA y su configuración de límites asociada.
    Cifra las claves de API personalizadas antes de guardarlas.
    """
    # Cifrar claves de API si se suministraron en settings
    settings_dict = payload.agentSettings.copy() if payload.agentSettings else {}
    for key in ["openai_api_key", "gemini_api_key", "anthropic_api_key", "openrouter_api_key"]:
        if key in settings_dict and settings_dict[key]:
            settings_dict[key] = encrypt_key(settings_dict[key])
            
    # Guardar campos extra en settings_dict
    settings_dict["ai_tools"] = payload.aiTools or "[]"
    settings_dict["ai_fallback_models"] = payload.aiFallbackModels or "[]"
    settings_dict["ai_knowledge_base"] = payload.aiKnowledgeBase or ""
    settings_dict["ai_vision_model"] = payload.aiVisionModel
    if payload.workflow_graph:
        settings_dict["workflow_graph"] = payload.workflow_graph
    
    agent = Agent(
        id=uuid.uuid4().hex,
        name=payload.name,
        avatar=payload.avatar,
        agent_type=(payload.agentType or "conversational").upper(),
        ai_model=payload.aiModel or "gpt-4o-mini",
        ai_system_prompt=payload.aiSystemPrompt or "Eres un útil y amable asistente virtual.",
        ai_temperature=payload.aiTemperature or 0.7,
        ai_tone=payload.aiTone or "Profesional y amable",
        ai_guardrails=payload.aiGuardrails or "",
        agent_settings=settings_dict
    )
    db.add(agent)
    await db.flush()
    
    # Crear configuración de límites
    cfg_payload = payload.config or AgentConfigSchema()
    config = AgentConfig(
        id=uuid.uuid4().hex,
        agent_id=agent.id,
        max_loops=cfg_payload.max_loops,
        max_tokens_per_run=cfg_payload.max_tokens_per_run,
        input_schema=cfg_payload.input_schema,
        output_schema=cfg_payload.output_schema
    )
    db.add(config)
    
    await db.commit()
    await db.refresh(agent)
    
    return {
        "id": agent.id,
        "name": agent.name,
        "ai_model": agent.ai_model,
        "ai_system_prompt": agent.ai_system_prompt,
        "created_at": agent.created_at.isoformat() if agent.created_at else None
    }


@router.post("/tools/discover")
async def discover_tool(
    request: dict,
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    scaffold = generate_tool_scaffold(request.get("description", ""))
    return scaffold


@router.get("/prompt-templates")
async def list_prompt_templates(
    category: str = Query(""),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    return {"templates": get_templates(category) if category else get_templates()}


@router.get("/prompt-templates/{template_id}")
async def get_prompt_template(
    template_id: str,
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    template = get_template_by_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_agent(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    import zipfile, io, json
    content = await file.read()
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = zf.namelist()
            package_file = next((n for n in names if n.endswith("package.json")), None)
            if not package_file:
                raise HTTPException(status_code=400, detail="No package.json found in archive")
            package_json = zf.read(package_file).decode("utf-8")
        result = await import_agent_package(db, package_json)
        return result
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid package.json")


@router.get("/marketplace/list")
async def browse_marketplace(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    return {"agents": await get_marketplace_agents(db)}


@router.get("/export-all")
async def export_all_agents(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    result = await db.execute(select(Agent).order_by(Agent.created_at.desc()))
    agents = result.scalars().all()
    export_list = []
    for a in agents:
        cfg = (await db.execute(select(AgentConfig).where(AgentConfig.agent_id == a.id))).scalar_one_or_none()
        export_list.append({
            "id": a.id, "name": a.name, "agent_type": a.agent_type,
            "ai_model": a.ai_model, "ai_system_prompt": a.ai_system_prompt,
            "ai_temperature": a.ai_temperature, "ai_tone": a.ai_tone,
            "ai_guardrails": a.ai_guardrails,
            "tools": a.agent_settings.get("ai_tools") if a.agent_settings else [],
            "max_loops": cfg.max_loops if cfg else 10,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return {"agents": export_list, "total": len(export_list)}


# ═══════════════════════════════════════════════════════════════════
# Dynamic agent_id routes below — static routes must be above
# ═══════════════════════════════════════════════════════════════════

@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Obtiene los detalles de configuración completos de un agente.
    """
    agent_res = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_res.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
        
    cfg_res = await db.execute(select(AgentConfig).where(AgentConfig.agent_id == agent_id))
    config = cfg_res.scalar_one_or_none()
    
    # Retornar settings sin revelar contraseñas
    safe_settings = agent.agent_settings.copy() if agent.agent_settings else {}
    for key in ["openai_api_key", "gemini_api_key", "anthropic_api_key", "openrouter_api_key"]:
        if key in safe_settings and safe_settings[key]:
            safe_settings[key] = "********" # Enmascarar la API key
            
    # Extraer campos de settings
    ai_tools = safe_settings.pop("ai_tools", "[]")
    ai_fallback_models = safe_settings.pop("ai_fallback_models", "[]")
    ai_knowledge_base = safe_settings.pop("ai_knowledge_base", "")
    ai_vision_model = safe_settings.pop("ai_vision_model", None)
            
    return {
        "id": agent.id,
        "name": agent.name,
        "avatar": agent.avatar,
        "agentType": agent.agent_type.upper() if agent.agent_type else "CONVERSATIONAL",
        "aiModel": agent.ai_model,
        "aiSystemPrompt": agent.ai_system_prompt,
        "aiTemperature": agent.ai_temperature,
        "aiTone": agent.ai_tone,
        "aiGuardrails": agent.ai_guardrails,
        "aiTools": ai_tools,
        "aiFallbackModels": ai_fallback_models,
        "aiKnowledgeBase": ai_knowledge_base,
        "aiVisionModel": ai_vision_model,
        "workflow_graph": safe_settings.pop("workflow_graph", None),
        "agentSettings": safe_settings,
        "is_active": agent.is_active,
        "config": {
            "max_loops": config.max_loops if config else 10,
            "max_tokens_per_run": config.max_tokens_per_run if config else 50000,
            "input_schema": config.input_schema if config else {},
            "output_schema": config.output_schema if config else {}
        } if config else None
    }

@router.patch("/{agent_id}")
async def update_agent(
    agent_id: str,
    payload: AgentUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Actualiza la configuración de un agente.
    Cifra las claves de API personalizadas si se modifican.
    """
    agent_res = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_res.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
        
    if payload.name is not None:
        agent.name = payload.name
    if payload.avatar is not None:
        agent.avatar = payload.avatar
    if payload.agentType is not None:
        agent.agent_type = payload.agentType.upper()
    if payload.aiModel is not None:
        agent.ai_model = payload.aiModel
    if payload.aiSystemPrompt is not None:
        agent.ai_system_prompt = payload.aiSystemPrompt
    if payload.aiTemperature is not None:
        agent.ai_temperature = payload.aiTemperature
    if payload.aiTone is not None:
        agent.ai_tone = payload.aiTone
    if payload.aiGuardrails is not None:
        agent.ai_guardrails = payload.aiGuardrails
    if payload.is_active is not None:
        agent.is_active = payload.is_active
        
    # Mezclar configuraciones
    settings_dict = agent.agent_settings.copy() if agent.agent_settings else {}
    if payload.agentSettings is not None:
        for key, val in payload.agentSettings.items():
            if key in ["openai_api_key", "gemini_api_key", "anthropic_api_key", "openrouter_api_key"]:
                if val == "********":
                    # No cambiar la clave existente si no se editó
                    continue
                settings_dict[key] = encrypt_key(val)
            else:
                settings_dict[key] = val
                
    if payload.aiTools is not None:
        settings_dict["ai_tools"] = payload.aiTools
    if payload.aiFallbackModels is not None:
        settings_dict["ai_fallback_models"] = payload.aiFallbackModels
    if payload.aiKnowledgeBase is not None:
        settings_dict["ai_knowledge_base"] = payload.aiKnowledgeBase
    if payload.aiVisionModel is not None:
        settings_dict["ai_vision_model"] = payload.aiVisionModel
    if payload.workflow_graph is not None:
        settings_dict["workflow_graph"] = payload.workflow_graph
        
    agent.agent_settings = settings_dict
        
    if payload.config is not None:
        cfg_res = await db.execute(select(AgentConfig).where(AgentConfig.agent_id == agent_id))
        config = cfg_res.scalar_one_or_none()
        if config:
            config.max_loops = payload.config.max_loops
            config.max_tokens_per_run = payload.config.max_tokens_per_run
            config.input_schema = payload.config.input_schema
            config.output_schema = payload.config.output_schema

    user_email = current_user.get("email", "unknown")
    store = get_prompt_store()
    store.save_version(
        agent_id=agent_id,
        prompt_text=agent.ai_system_prompt,
        guardrails=agent.ai_guardrails or "",
        tone=agent.ai_tone or "",
        tools=str(agent.agent_settings.get("ai_tools", "[]")) if agent.agent_settings else "[]",
        changed_by=user_email,
    )

    await db.commit()
    return {"status": "success", "message": "Agente actualizado exitosamente"}

@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Elimina un agente y todas sus dependencias en cascada.
    """
    agent_res = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_res.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
        
    await db.delete(agent)
    await db.commit()
    return {"status": "success", "message": "Agente eliminado exitosamente"}

@limiter.limit("30/minute")
@router.post("/{agent_id}/run")
async def run_agent(
    agent_id: str,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Ejecuta el agente de IA en modo interactivo (conversación de chat).
    """
    try:
        input_payload = {
            "message": payload.message,
            "user_id": current_user.get("sub", "").split("|")[-1]
        }
        if payload.collected_data:
            input_payload.update(payload.collected_data)
            
        result = await execute_agent_run(db, agent_id, input_payload, trigger_source="manual")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@limiter.limit("30/minute")
@router.post("/{agent_id}/stream")
async def stream_agent(
    agent_id: str,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    input_payload = {
        "message": payload.message,
        "user_id": current_user.get("sub", "").split("|")[-1]
    }
    if payload.collected_data:
        input_payload.update(payload.collected_data)

    async def event_generator():
        try:
            async for event in execute_agent_run_streaming(db, agent_id, input_payload, trigger_source="manual"):
                yield f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{agent_id}/execution-runs")
async def list_execution_runs(
    agent_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Lista el historial de ejecuciones de un agente.
    """
    result = await db.execute(
        select(AgentExecutionRun)
        .where(AgentExecutionRun.agent_id == agent_id)
        .order_by(AgentExecutionRun.created_at.desc())
        .limit(50)
    )
    runs = result.scalars().all()
    return [
        {
            "id": r.id,
            "trigger_source": r.trigger_source,
            "status": r.status,
            "loop_count": r.loop_count,
            "token_usage": r.token_usage,
            "cost_usd": r.cost_usd,
            "latency_ms": r.latency_ms,
            "created_at": r.created_at.isoformat()
        } for r in runs
    ]

@router.post("/{agent_id}/knowledge")
async def add_knowledge_doc(
    agent_id: str,
    payload: RAGDocumentCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Sube un documento y genera embeddings de base de conocimiento (RAG) para el agente.
    """
    try:
        doc = await add_document_to_knowledge(
            db=db,
            agent_id=agent_id,
            filename=payload.filename,
            content=payload.content
        )
        return {
            "id": doc.id,
            "filename": doc.filename,
            "created_at": doc.created_at.isoformat(),
            "status": "indexed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}/knowledge")
async def list_knowledge_docs(
    agent_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Lista los documentos indexados en la base de conocimiento del agente.
    """
    result = await db.execute(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.agent_id == agent_id)
        .order_by(KnowledgeDocument.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "created_at": d.created_at.isoformat()
        } for d in docs
    ]

@router.delete("/{agent_id}/knowledge/{doc_id}")
async def delete_knowledge_doc(
    agent_id: str,
    doc_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Elimina un documento indexado y purga todos sus vectores/chunks.
    """
    result = await db.execute(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.agent_id == agent_id, KnowledgeDocument.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
        
    await db.delete(doc)
    await db.commit()
    return {"status": "success", "message": "Documento y vectores eliminados exitosamente"}


@router.post("/{agent_id}/knowledge/upload", status_code=status.HTTP_201_CREATED)
async def upload_knowledge_file(
    agent_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """Sube un archivo (PDF, DOCX, TXT, CSV, JSON, MD) y lo indexa en la base de conocimiento."""
    allowed_types = {
        "text/plain", "text/csv", "application/json", "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    if file.content_type and file.content_type not in allowed_types:
        file_ext = file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
        if file_ext not in ("txt", "csv", "json", "pdf", "docx", "xlsx", "md", "py", "ts", "tsx", "js", "html", "css", "yaml", "yml"):
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type or file_ext}")

    content_bytes = await file.read()
    extracted_text = await parse_file_content(file.filename or "unknown", content_bytes, file.content_type)

    if not extracted_text or extracted_text.startswith("[PDF content requires") or extracted_text.startswith("[DOCX content requires") or extracted_text.startswith("[PDF parse error") or extracted_text.startswith("[DOCX parse error"):
        raise HTTPException(status_code=400, detail=f"Could not extract text from file. Install required libraries (PyPDF2, python-docx).")

    try:
        doc = await add_document_to_knowledge(
            db=db,
            agent_id=agent_id,
            filename=file.filename or "uploaded_file",
            content=extracted_text
        )
        return {
            "id": doc.id,
            "filename": doc.filename,
            "chars_extracted": len(extracted_text),
            "created_at": doc.created_at.isoformat(),
            "status": "indexed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/prompt-versions")
async def get_prompt_versions(
    agent_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    store = get_prompt_store()
    agent_res = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_res.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "agent_id": agent_id,
        "current_prompt": agent.ai_system_prompt,
        "versions": store.get_history(agent_id),
    }


@router.post("/{agent_id}/prompt-versions/rollback")
async def rollback_prompt_version(
    agent_id: str,
    version: int = Query(...),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    store = get_prompt_store()
    agent_res = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_res.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    rolled = store.rollback(agent_id, version, current_user.get("email", "unknown"))
    if not rolled:
        raise HTTPException(status_code=404, detail=f"Version {version} not found")

    agent.ai_system_prompt = rolled["system_prompt"]
    agent.ai_guardrails = rolled["guardrails"]
    agent.ai_tone = rolled["tone"]
    if rolled.get("tools"):
        agent.agent_settings = agent.agent_settings or {}
        agent.agent_settings["ai_tools"] = rolled["tools"]
    await db.commit()

    return {"status": "rolled_back", "version": rolled["version"], "message": f"Prompt rolled back to v{version}"}


class TriggerScheduleIn(BaseModel):
    cron: str
    description: str = ""


@router.post("/{agent_id}/triggers", status_code=status.HTTP_201_CREATED)
async def schedule_trigger(
    agent_id: str,
    body: TriggerScheduleIn,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    agent_res = await db.execute(select(Agent).where(Agent.id == agent_id))
    if not agent_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")
    return schedule_agent_trigger(agent_id, body.cron, body.description)


@router.get("/{agent_id}/triggers")
async def get_triggers(agent_id: str):
    return {"triggers": list_scheduled_triggers(agent_id)}


@router.delete("/{agent_id}/triggers/{trigger_id}")
async def delete_trigger(agent_id: str, trigger_id: str):
    ok = remove_scheduled_trigger(trigger_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return {"status": "deleted"}


@router.get("/{agent_id}/export", response_class=Response)
async def export_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from fastapi.responses import Response
    try:
        zip_bytes = await export_agent_package(db, agent_id)
        agent_res = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = agent_res.scalar_one_or_none()
        name = agent.name.lower().replace(" ", "_") if agent else agent_id
        return Response(content=zip_bytes, media_type="application/zip",
                        headers={"Content-Disposition": f"attachment; filename=agent_{name}.zip"})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/workflows/validate")
async def validate_workflow(
    payload: dict,
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.schemas.workflow import WorkflowGraph
    from pydantic import ValidationError
    
    errors = []
    warnings = []
    is_valid = True
    
    try:
        # Pydantic validation
        graph = WorkflowGraph(**payload)
        
        # Logical validation
        has_start = False
        for node in graph.nodes:
            if node.type == "start":
                has_start = True
            elif node.type == "llm" and not node.data.get("prompt"):
                warnings.append(f"LLM node {node.id} has no prompt defined")
                
        if not has_start:
            warnings.append("Workflow has no start node")
            
    except ValidationError as e:
        is_valid = False
        for err in e.errors():
            loc = ".".join(str(l) for l in err["loc"])
            errors.append(f"Validation error at {loc}: {err['msg']}")
    except Exception as e:
        is_valid = False
        errors.append(str(e))
        
    return {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings
    }

# ── Fleet Management ─────────────────────────────────────────────────────────


@router.post("/fleet/deploy")
async def deploy_agent_fleet_endpoint(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["sys_admin"]))
):
    from app.services.agent_fleet import deploy_agent_fleet
    result = await deploy_agent_fleet(db)
    return {
        "status": "ok",
        "created": result["created"],
        "updated": result["updated"],
        "skipped": result["skipped"],
        "total": len(result["created"]) + len(result["updated"]),
    }


@router.get("/fleet/status")
async def get_fleet_status_endpoint(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.services.agent_fleet import get_fleet_status
    agents = await get_fleet_status(db)
    total_runs = sum(a["total_runs"] for a in agents)
    active_count = sum(1 for a in agents if a["active"] and a.get("present_in_db"))
    return {
        "agents": agents,
        "summary": {
            "total_defined": len(agents),
            "active_in_db": active_count,
            "total_runs_all": total_runs,
        },
    }


@router.get("/{agent_id}/health")
async def get_agent_health(
    agent_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"])),
):
    from app.services.agent_health import check_agent_health
    try:
        health = await check_agent_health(agent_id, db)
        await db.commit()
        return {"success": True, **health}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")


@router.get("/health/dashboard")
async def get_health_dashboard(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"])),
):
    from app.services.agent_health import check_agent_health
    from app.models.agent import Agent, AgentHealthRecord
    from sqlalchemy import desc

    result = await db.execute(select(Agent).where(Agent.is_active == True))
    agents = list(result.scalars().all())

    health_summary = []
    for agent in agents:
        latest_result = await db.execute(
            select(AgentHealthRecord)
            .where(AgentHealthRecord.agent_id == agent.id)
            .order_by(AgentHealthRecord.checked_at.desc())
            .limit(1)
        )
        latest = latest_result.scalar_one_or_none()
        if latest:
            health_summary.append({
                "agent_id": agent.id,
                "name": agent.name,
                "agent_type": agent.agent_type,
                "status": latest.status,
                "response_time_ms": latest.response_time_ms,
                "error_message": latest.error_message,
                "checked_at": latest.checked_at.isoformat() if latest.checked_at else None,
            })
        else:
            health_summary.append({
                "agent_id": agent.id,
                "name": agent.name,
                "agent_type": agent.agent_type,
                "status": "unknown",
                "response_time_ms": 0,
                "error_message": None,
                "checked_at": None,
            })

    healthy = sum(1 for h in health_summary if h["status"] == "healthy")
    degraded = sum(1 for h in health_summary if h["status"] == "degraded")
    unhealthy = sum(1 for h in health_summary if h["status"] == "unhealthy")
    unknown = sum(1 for h in health_summary if h["status"] == "unknown")

    return {
        "success": True,
        "summary": {
            "total": len(health_summary),
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy": unhealthy,
            "unknown": unknown,
        },
        "agents": health_summary,
    }


@router.post("/{agent_id}/certify/{skill_name}")
async def certify_agent_skill(
    agent_id: str,
    skill_name: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.skill_certification import SkillCertification
    result = await SkillCertification.certify_skill(agent_id, skill_name, db)
    return result.to_dict()


@router.get("/{agent_id}/certifications")
async def list_certifications(
    agent_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.services.skill_certification import SkillCertification
    certs = await SkillCertification.get_certifications(agent_id, db)
    return {"certifications": certs}


@router.get("/{agent_id}/certifications/{skill_name}")
async def get_certification_status(
    agent_id: str,
    skill_name: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.services.skill_certification import SkillCertification
    status = await SkillCertification.get_certification_status(agent_id, skill_name, db)
    if status is None:
        raise HTTPException(status_code=404, detail="No certification found for this skill")
    return status


@router.get("/reputation/leaderboard")
async def get_reputation_leaderboard(
    limit: int = Query(10, ge=1, le=50),
    category: str = Query("overall", pattern="^(overall|cost_efficiency|user_satisfaction|task_completion)$"),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.services.agent_reputation import AgentReputation
    board = await AgentReputation.get_leaderboard(limit=limit, category=category, db=db)
    return {"leaderboard": board, "category": category}


@router.get("/{agent_id}/reputation")
async def get_agent_reputation(
    agent_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.services.agent_reputation import AgentReputation, get_cached_reputation
    cached = await get_cached_reputation(agent_id)
    if cached:
        return cached
    rep = await AgentReputation.calculate_reputation(agent_id, db)
    return rep


@router.get("/{agent_id}/reputation/drift")
async def detect_agent_drift(
    agent_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.agent_reputation import AgentReputation
    drift = await AgentReputation.detect_drift(agent_id, db)
    return drift


@router.get("/pools/stats")
async def get_pool_stats(
    current_user: dict = Depends(require_roles(["sys_admin"]))
):
    from app.services.agent_pool import AgentPoolManager
    stats = await AgentPoolManager.get_all_pool_stats()
    return {"pools": stats}


# --- A/B Deployment ---

class CreateABVariantBody(BaseModel):
    variant_settings: dict
    traffic_split: float = 0.1


@router.post("/{agent_id}/ab/create")
async def create_ab_variant(
    agent_id: str,
    body: CreateABVariantBody,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.ab_deployment import ABDeployment
    try:
        result = await ABDeployment.create_variant(
            agent_id,
            body.variant_settings,
            body.traffic_split,
            db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{agent_id}/ab/compare")
async def compare_ab_variants(
    agent_id: str,
    period_days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.ab_deployment import ABDeployment
    return await ABDeployment.compare_variants(agent_id, db, period_days)


@router.post("/{agent_id}/ab/promote/{variant_id}")
async def promote_ab_variant(
    agent_id: str,
    variant_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.ab_deployment import ABDeployment
    try:
        result = await ABDeployment.promote_variant(variant_id, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{agent_id}/ab/rollback")
async def rollback_ab_variants(
    agent_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.ab_deployment import ABDeployment
    return await ABDeployment.auto_rollback(agent_id, db)


# ── Skill Template Endpoints ───────────────────────────────────────────────


@router.get("/templates")
async def list_skill_templates(
    category: Optional[str] = Query(None),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.services.skill_marketplace import list_templates
    templates = await list_templates(category)
    return {"templates": templates, "total": len(templates)}


@router.get("/templates/{template_id}")
async def get_skill_template(
    template_id: str,
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    from app.services.skill_marketplace import get_template
    template = await get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/templates/{template_id}/install", status_code=status.HTTP_201_CREATED)
async def install_skill_template(
    template_id: str,
    name: str = Query(..., description="Name for the new agent"),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.skill_marketplace import install_template
    try:
        result = await install_template(template_id, name, current_user["sub"], db)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Benchmark Endpoints ────────────────────────────────────────────────────


@router.post("/{agent_id}/benchmark")
async def run_agent_benchmark(
    agent_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.evaluation_benchmarks import run_benchmark
    try:
        result = await run_benchmark(agent_id, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{agent_id}/benchmarks")
async def list_agent_benchmarks(
    agent_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    stmt = (
        select(BenchmarkRun)
        .where(BenchmarkRun.agent_id == agent_id)
        .order_by(BenchmarkRun.created_at.desc())
        .limit(20)
    )
    result = await db.execute(stmt)
    runs = result.scalars().all()
    return {
        "agent_id": agent_id,
        "benchmarks": [
            {
                "id": r.id,
                "overall_score": r.overall_score,
                "scenarios_total": r.scenarios_total,
                "scenarios_ran": r.scenarios_ran,
                "avg_latency_ms": r.avg_latency_ms,
                "total_cost_usd": r.total_cost_usd,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ]
    }


@router.get("/benchmarks/latest")
async def get_latest_benchmarks(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from sqlalchemy import func as sqlfunc, distinct

    subq = (
        select(
            BenchmarkRun.agent_id,
            sqlfunc.max(BenchmarkRun.created_at).label("max_created"),
        )
        .group_by(BenchmarkRun.agent_id)
        .subquery()
    )

    stmt = select(BenchmarkRun).join(
        subq,
        (BenchmarkRun.agent_id == subq.c.agent_id)
        & (BenchmarkRun.created_at == subq.c.max_created),
    )

    result = await db.execute(stmt)
    runs = result.scalars().all()

    return {
        "latest": [
            {
                "agent_id": r.agent_id,
                "agent_type": r.agent_type,
                "overall_score": r.overall_score,
                "scenarios_ran": r.scenarios_ran,
                "avg_latency_ms": r.avg_latency_ms,
                "total_cost_usd": r.total_cost_usd,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ]
    }


class ResumeRunRequest(BaseModel):
    approved: bool
    rejection_reason: Optional[str] = None


@router.post("/runs/{run_id}/resume")
async def resume_run(
    run_id: str,
    payload: ResumeRunRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin", "admin", "legal_manager"]))
):
    """
    Resume a paused agent execution run after administrative approval/rejection.
    """
    from app.services.agent_executor import resume_agent_run
    try:
        result = await resume_agent_run(
            db=db,
            run_id=run_id,
            approved=payload.approved,
            approver_id=current_user.get("sub", "").split("|")[-1],
            rejection_reason=payload.rejection_reason
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/specialists", response_model=dict)
async def list_specialists(db: AsyncSession = Depends(get_tenant_db)):
    from app.services.specialist_registry import get_specialists_summary
    return {"specialists": get_specialists_summary()}


@router.get("/specialists/active", response_model=dict)
async def list_active_specialists(db: AsyncSession = Depends(get_tenant_db)):
    from app.services.specialist_registry import discover_active_specialists
    specialists = await discover_active_specialists(db)
    return {"active_specialists": specialists}


@router.get("/specialists/health", response_model=dict)
async def get_specialists_health(db: AsyncSession = Depends(get_tenant_db)):
    from app.services.specialist_registry import get_specialist_health
    health_data = await get_specialist_health(db)
    return {"health": health_data}


@router.get("/analytics/agent/{agent_id}", response_model=dict)
async def get_agent_analytics(agent_id: str, hours: int = 24, db: AsyncSession = Depends(get_tenant_db)):
    from app.services.agent_analytics_collector import agent_analytics
    metrics = await agent_analytics.get_agent_metrics(agent_id, db, window_hours=hours)
    return {"agent_id": agent_id, "window_hours": hours, "metrics": metrics}


@router.get("/analytics/platform", response_model=dict)
async def get_platform_analytics(db: AsyncSession = Depends(get_tenant_db)):
    from app.services.agent_analytics_collector import agent_analytics
    summary = await agent_analytics.get_platform_summary(db)
    return {"platform_summary": summary}


@router.get("/pool/status", response_model=dict)
async def get_agent_pool_status():
    from app.services.agent_pool_v2 import agent_pool_v2
    stats = await agent_pool_v2.get_stats()
    return {
        "pool_size": stats.pool_size,
        "active_agents": stats.active_agents,
        "idle_agents": stats.idle_agents,
        "total_runs": stats.total_runs,
        "avg_agent_latency_ms": stats.avg_agent_latency_ms,
        "agent_types": stats.agent_types,
    }


@router.get("/health/summary", response_model=dict)
async def get_all_agents_health(db: AsyncSession = Depends(get_tenant_db)):
    from app.services.agent_health import get_all_agents_health_summary
    return {"health_summary": await get_all_agents_health_summary(db)}


@router.get("/model-catalog", response_model=dict)
async def get_model_catalog():
    from app.services.model_catalog import get_catalog_summary
    return {"models": get_catalog_summary()}


@router.get("/runtime/stats", response_model=dict)
async def get_runtime_stats():
    from app.services.runtime_monitor import get_executor_health
    return {"runtime_stats": get_executor_health()}


@router.get("/runtime/tasks", response_model=dict)
async def get_supervised_tasks_status():
    from app.services.runtime_monitor import get_task_supervisor
    supervisor = get_task_supervisor()
    return {"tasks": await supervisor.get_status()}


@router.get("/eu-ai-act/compliance", response_model=dict)
async def get_eu_ai_act_compliance(request: Request, current_user: dict = Depends(get_current_user)):
    tenant_id = current_user.get("tenant_id", "default")
    from app.services.eu_ai_act import get_eu_ai_act_compliance_summary
    return await get_eu_ai_act_compliance_summary(tenant_id)


@router.get("/eu-ai-act/transparency", response_model=dict)
async def get_ai_transparency_report(hours: int = 24, current_user: dict = Depends(get_current_user)):
    tenant_id = current_user.get("tenant_id", "default")
    from app.services.eu_ai_act import get_transparency_report
    return await get_transparency_report(tenant_id, hours)


@router.get("/eu-ai-act/classify/{agent_type}", response_model=dict)
async def classify_agent_risk(agent_type: str):
    from app.services.eu_ai_act import classify_agent_risk, get_risk_mitigations
    classification = await classify_agent_risk(agent_type)
    classification["mitigations"] = await get_risk_mitigations(classification["risk_category"])
    return classification


# ── Crew Orchestration Endpoints ─────────────────────────────────────────────


@limiter.limit("10/minute")
@router.post("/crew/execute")
async def execute_crew_task(
    request: CrewTaskRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.agent_crew import execute_crew_task

    try:
        result = await execute_crew_task(
            task=request.task,
            agent_ids=request.agent_ids,
            max_parallel=request.max_parallel,
            worker_timeout=request.worker_timeout_seconds,
            db=db,
            user_id=current_user.get("sub", "").split("|")[-1],
            tenant_id=current_user.get("tenant_id", "default"),
        )
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@limiter.limit("10/minute")
@router.post("/crew/stream")
async def crew_stream(
    request: CrewTaskRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.agent_crew import execute_crew_task

    user_id = current_user.get("sub", "").split("|")[-1]
    tenant_id = current_user.get("tenant_id", "default")

    progress_events: list[dict] = []

    async def progress_callback(event_type: str, data: dict):
        progress_events.append({"event": event_type, "data": data})

    async def event_generator():
        import asyncio as _asyncio

        async def run_task():
            return await execute_crew_task(
                task=request.task,
                agent_ids=request.agent_ids,
                max_parallel=request.max_parallel,
                worker_timeout=request.worker_timeout_seconds,
                db=db,
                user_id=user_id,
                tenant_id=tenant_id,
                progress_callback=progress_callback,
            )

        loop = _asyncio.get_event_loop()
        future = _asyncio.ensure_future(run_task())

        sent_events = 0
        while not future.done():
            while sent_events < len(progress_events):
                ev = progress_events[sent_events]
                yield f"event: {ev['event']}\ndata: {json.dumps(ev['data'], ensure_ascii=False)}\n\n"
                sent_events += 1
            await _asyncio.sleep(0.1)

        while sent_events < len(progress_events):
            ev = progress_events[sent_events]
            yield f"event: {ev['event']}\ndata: {json.dumps(ev['data'], ensure_ascii=False)}\n\n"
            sent_events += 1

        try:
            result = future.result()
            yield f"event: crew_complete\ndata: {json.dumps(result.model_dump(), ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Swarm Orchestration Endpoints ────────────────────────────────────────────


@limiter.limit("10/minute")
@router.post("/swarm/run")
async def run_swarm(
    request: SwarmRunRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.agent_swarm import execute_swarm_run

    user_id = current_user.get("sub", "").split("|")[-1]

    starting_agent_id = request.starting_agent_id
    if not starting_agent_id:
        agents_res = await db.execute(select(Agent).where(Agent.is_active == True).limit(1))
        first = agents_res.scalar_one_or_none()
        if first:
            starting_agent_id = first.id
        else:
            raise HTTPException(status_code=400, detail="No active agents available")

    try:
        result = await execute_swarm_run(
            task=request.task,
            starting_agent_id=starting_agent_id,
            max_handoffs=request.max_handoffs,
            agent_ids=request.agent_ids,
            db=db,
            user_id=user_id,
            tenant_id=current_user.get("tenant_id", "default"),
        )
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@limiter.limit("10/minute")
@router.post("/swarm/stream")
async def stream_swarm(
    request: SwarmRunRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.agent_swarm import execute_swarm_run

    user_id = current_user.get("sub", "").split("|")[-1]
    tenant_id = current_user.get("tenant_id", "default")

    agents_res = await db.execute(select(Agent).where(Agent.is_active == True).limit(1))
    first = agents_res.scalar_one_or_none()
    if not request.starting_agent_id and not first:
        raise HTTPException(status_code=400, detail="No active agents available")

    starting_agent_id = request.starting_agent_id or first.id

    progress_events: list[dict] = []

    async def progress_callback(event_type: str, data: dict):
        progress_events.append({"event": event_type, "data": data})

    async def event_generator():
        import asyncio as _asyncio

        async def run_task():
            return await execute_swarm_run(
                task=request.task,
                starting_agent_id=starting_agent_id,
                max_handoffs=request.max_handoffs,
                agent_ids=request.agent_ids,
                db=db,
                user_id=user_id,
                tenant_id=tenant_id,
                progress_callback=progress_callback,
            )

        loop = _asyncio.get_event_loop()
        future = _asyncio.ensure_future(run_task())

        sent_events = 0
        while not future.done():
            while sent_events < len(progress_events):
                ev = progress_events[sent_events]
                yield f"event: {ev['event']}\ndata: {json.dumps(ev['data'], ensure_ascii=False)}\n\n"
                sent_events += 1
            await _asyncio.sleep(0.1)

        while sent_events < len(progress_events):
            ev = progress_events[sent_events]
            yield f"event: {ev['event']}\ndata: {json.dumps(ev['data'], ensure_ascii=False)}\n\n"
            sent_events += 1

        try:
            result = future.result()
            yield f"event: swarm_complete\ndata: {json.dumps(result.model_dump(), ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

