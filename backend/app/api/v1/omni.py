from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import subprocess
import os
import uuid

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.dependencies import get_tenant_db, require_roles
from app.models.agent import Agent, AgentConfig, AgentExecutionRun
from app.services.omni_runtime import list_files, read_file, write_file, execute_omni_master, execute_orchestration, sanitize_path, WORKSPACE_ROOT
from app.services.llm_router import get_dynamic_models
from app.services.branch_edit_manager import BranchEditManager
from app.models.branch_edit import BranchSession, FileProposal

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


async def _get_or_create_omni_agent(db: AsyncSession) -> Agent:
    agent_res = await db.execute(
        select(Agent).where(Agent.agent_type == "OMNI_MASTER").order_by(Agent.created_at.desc()).limit(1)
    )
    agent = agent_res.scalar_one_or_none()
    if agent:
        return agent

    agent = Agent(
        id=uuid.uuid4().hex, name="Omni Master Controller", avatar="\U0001f30c",
        agent_type="OMNI_MASTER", ai_model="gpt-4o-mini",
        ai_system_prompt="Eres el Omni Master Controller de SuccessCore. Responde en formato JSON usando las herramientas disponibles.",
        ai_temperature=0.2, ai_tone="Profesional", agent_settings={},
    )
    db.add(agent)
    await db.flush()
    config = AgentConfig(id=uuid.uuid4().hex, agent_id=agent.id, max_loops=10, max_tokens_per_run=100000)
    db.add(config)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/models")
async def get_omni_models():
    return {"models": await get_dynamic_models()}

# --- Pydantic Schemas ---
class FileWritePayload(BaseModel):
    path: str
    content: str

class MasterExecutePayload(BaseModel):
    prompt: str

class MasterConfigPayload(BaseModel):
    name: Optional[str] = None
    aiModel: Optional[str] = None
    aiSystemPrompt: Optional[str] = None
    aiTemperature: Optional[float] = None
    aiTone: Optional[str] = None
    aiGuardrails: Optional[str] = None
    aiTools: Optional[str] = None
    aiFallbackModels: Optional[str] = None
    maxLoops: Optional[int] = None

class OrchestratePayload(BaseModel):
    message: str
    max_sub_agents: int = 5

class EditModePayload(BaseModel):
    mode: str  # "direct" or "proposal"
    auto_create_branch: Optional[bool] = None
    require_approval: Optional[bool] = None
    repo_url: Optional[str] = None

class BranchCreatePayload(BaseModel):
    base_branch: str = "main"

class ProposalReviewPayload(BaseModel):
    reason: Optional[str] = None

class PRCreatePayload(BaseModel):
    title: str
    body: str = ""

# --- Routes ---

@router.get("/files")
async def get_codebase_files(
    action: str = Query("list", description="list or read"),
    path: str = Query(".", description="Relative path in workspace"),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Lista archivos o lee un archivo específico de la codebase del workspace.
    """
    try:
        if action == "read":
            content = read_file(path)
            return {"content": content}
        else:
            files = list_files(path)
            parsed_files = []
            for f in files:
                is_dir = f.endswith("(DIR)")
                clean_path = f.replace(" (DIR)", "").replace(" (FILE)", "")
                ext = clean_path.split(".")[-1] if "." in clean_path else ""
                
                language = "plaintext"
                if ext in ["js", "jsx"]:
                    language = "javascript"
                elif ext in ["ts", "tsx"]:
                    language = "typescript"
                elif ext == "json":
                    language = "json"
                elif ext == "md":
                    language = "markdown"
                elif ext == "css":
                    language = "css"
                elif ext == "html":
                    language = "html"
                    
                parsed_files.append({
                    "path": clean_path,
                    "isDir": is_dir,
                    "language": language
                })
            return {"files": parsed_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/files")
@limiter.limit("30/minute")
async def save_codebase_file(
    payload: FileWritePayload,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Guarda o modifica un archivo específico de la codebase del workspace.
    """
    try:
        result = write_file(payload.path, payload.content)
        if "Error" in result:
            raise HTTPException(status_code=400, detail=result)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/files")
@limiter.limit("30/minute")
async def delete_codebase_file(
    path: str = Query(..., description="Relative path of file to delete"),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Elimina un archivo específico de la codebase del workspace.
    """
    try:
        full_path = sanitize_path(path)
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="File not found")
        if os.path.isdir(full_path):
            raise HTTPException(status_code=400, detail="Cannot delete directories, only files.")
        os.remove(full_path)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/master")
async def get_omni_master(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    agent_res = await db.execute(
        select(Agent).where(Agent.agent_type == "OMNI_MASTER").order_by(Agent.created_at.desc()).limit(1)
    )
    agent = agent_res.scalar_one_or_none()
    if not agent:
        return {"id": None, "name": "Omni Master Controller", "agentType": "OMNI_MASTER", "aiModel": "gpt-4o-mini",
                "aiSystemPrompt": "", "agentConfig": None, "runs": []}
    cfg_res = await db.execute(select(AgentConfig).where(AgentConfig.agent_id == agent.id))
    config = cfg_res.scalar_one_or_none()
    return {
        "id": agent.id, "name": agent.name, "avatar": agent.avatar,
        "agentType": agent.agent_type, "aiModel": agent.ai_model,
        "aiSystemPrompt": agent.ai_system_prompt,
        "aiTemperature": agent.ai_temperature, "aiTone": agent.ai_tone,
        "aiGuardrails": agent.ai_guardrails,
        "aiTools": agent.agent_settings.get("ai_tools") if agent.agent_settings else "",
        "aiFallbackModels": agent.agent_settings.get("ai_fallback_models") if agent.agent_settings else "",
        "agentConfig": {"maxLoops": config.max_loops, "maxTokensPerRun": config.max_tokens_per_run} if config else None,
    }


@router.post("/master")
@limiter.limit("30/minute")
async def execute_omni_master_endpoint(
    payload: MasterExecutePayload,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    agent_res = await db.execute(select(Agent).where(Agent.agent_type == "OMNI_MASTER").order_by(Agent.created_at.desc()).limit(1))
    agent = agent_res.scalar_one_or_none()
    if not agent:
        agent = await _get_or_create_omni_agent(db)

    user_id = current_user.get("sub", "").split("|")[-1]
    try:
        result = await execute_omni_master(db, payload.prompt, user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orchestrate")
@limiter.limit("30/minute")
async def execute_orchestration_endpoint(
    payload: OrchestratePayload,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Run the OmniOrchestrator for complex multi-module HR requests.
    Decomposes the request, spawns specialized sub-agents, executes in parallel, and synthesizes results.
    """
    agent_res = await db.execute(select(Agent).where(Agent.agent_type == "OMNI_MASTER").order_by(Agent.created_at.desc()).limit(1))
    agent = agent_res.scalar_one_or_none()
    if not agent:
        agent = await _get_or_create_omni_agent(db)

    user_id = current_user.get("sub", "").split("|")[-1]
    try:
        result = await execute_orchestration(db, payload.message, user_id, max_sub_agents=payload.max_sub_agents)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/master")
@limiter.limit("30/minute")
async def configure_omni_agent(
    payload: MasterConfigPayload,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    try:
        agent_res = await db.execute(select(Agent).where(Agent.agent_type == "OMNI_MASTER").order_by(Agent.created_at.desc()).limit(1))
        agent = agent_res.scalar_one_or_none()
        if not agent:
            agent = await _get_or_create_omni_agent(db)

        data = payload.model_dump(exclude_unset=True)
        for field in ["name", "ai_system_prompt"]:
            if field in data:
                setattr(agent, field, data[field])
        if data.get("aiModel"):
            agent.ai_model = data["aiModel"]
        if data.get("aiTemperature") is not None:
            agent.ai_temperature = data["aiTemperature"]
        if data.get("aiTone") is not None:
            agent.ai_tone = data["aiTone"]
        if data.get("aiGuardrails") is not None:
            agent.ai_guardrails = data["aiGuardrails"]

        if data.get("aiTools") or data.get("aiFallbackModels"):
            settings_dict = dict(agent.agent_settings) if agent.agent_settings else {}
            if data.get("aiTools"):
                settings_dict["ai_tools"] = data["aiTools"]
            if data.get("aiFallbackModels"):
                settings_dict["ai_fallback_models"] = data["aiFallbackModels"]
            agent.agent_settings = settings_dict

        if data.get("maxLoops") is not None:
            cfg_res = await db.execute(select(AgentConfig).where(AgentConfig.agent_id == agent.id))
            config = cfg_res.scalar_one_or_none()
            if config:
                config.max_loops = data["maxLoops"]

        await db.commit()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/git-status")
async def get_git_status(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Devuelve los archivos modificados en el workspace ejecutando git status.
    """
    try:
        # Run git status --porcelain
        process = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=WORKSPACE_ROOT,
            capture_output=True,
            text=True,
        )
        if process.returncode != 0:
            return {"files": []}
            
        lines = [line.strip() for line in process.stdout.split("\n") if line.strip()]
        modified_files = []
        
        for line in lines:
            # Line format is e.g. " M filename.js"
            status_prefix = line[:2].strip()
            rel_path = line[2:].strip()
            
            # Remove surrounding quotes if git output has them
            if rel_path.startswith('"') and rel_path.endswith('"'):
                rel_path = rel_path[1:-1]
                
            try:
                full_path = sanitize_path(rel_path)
                if not os.path.exists(full_path) or os.path.isdir(full_path):
                    continue
                    
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                ext = rel_path.split(".")[-1] if "." in rel_path else ""
                language = "plaintext"
                if ext in ["js", "jsx"]:
                    language = "javascript"
                elif ext in ["ts", "tsx"]:
                    language = "typescript"
                elif ext == "json":
                    language = "json"
                elif ext == "md":
                    language = "markdown"
                    
                modified_files.append({
                    "path": rel_path,
                    "content": content,
                    "language": language
                })
            except Exception:
                continue
                
        return {"files": modified_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Branch Edit Mode Endpoints ---

@router.get("/edit-mode")
async def get_edit_mode(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    agent = await _get_or_create_omni_agent(db)
    manager = BranchEditManager()
    return await manager.get_edit_mode(agent.id, db)


@router.patch("/edit-mode")
@limiter.limit("30/minute")
async def set_edit_mode(
    payload: EditModePayload,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    agent = await _get_or_create_omni_agent(db)
    manager = BranchEditManager()
    settings = payload.model_dump(exclude_unset=True)
    success = await manager.set_edit_mode(agent.id, settings, db)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update edit mode")
    return {"success": True, "mode": payload.mode}


@router.post("/branches")
@limiter.limit("30/minute")
async def create_branch_session(
    payload: BranchCreatePayload,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    agent = await _get_or_create_omni_agent(db)
    user_id = current_user.get("sub", "").split("|")[-1]
    manager = BranchEditManager()
    session = await manager.initialize_branch(agent.id, payload.base_branch, user_id, db)
    return {
        "id": session.id,
        "branch_name": session.branch_name,
        "base_branch": session.base_branch,
        "status": session.status,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


@router.get("/branches/{branch_id}/proposals")
async def list_branch_proposals(
    branch_id: str,
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, applied, rejected"),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    manager = BranchEditManager()
    proposals = await manager.get_session_proposals(branch_id, db, status_filter=status_filter)
    return {
        "proposals": [
            {
                "id": p.id,
                "file_path": p.file_path,
                "status": p.status,
                "reason": p.reason,
                "proposed_by": p.proposed_by,
                "reviewed_by": p.reviewed_by,
                "review_notes": p.review_notes,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
            }
            for p in proposals
        ]
    }


@router.post("/proposals/{proposal_id}/apply")
@limiter.limit("30/minute")
async def apply_proposal(
    proposal_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    approver = current_user.get("email", current_user.get("sub", "unknown"))
    manager = BranchEditManager()
    try:
        proposal = await manager.apply_proposal(proposal_id, approver, db)
        return {"success": True, "status": proposal.status, "file_path": proposal.file_path}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proposals/{proposal_id}/reject")
@limiter.limit("30/minute")
async def reject_proposal(
    proposal_id: str,
    payload: ProposalReviewPayload,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    rejecter = current_user.get("email", current_user.get("sub", "unknown"))
    manager = BranchEditManager()
    try:
        proposal = await manager.reject_proposal(proposal_id, rejecter, payload.reason or "Rejected", db)
        return {"success": True, "status": proposal.status, "reason": proposal.review_notes}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/branches/{branch_id}/apply-all")
@limiter.limit("30/minute")
async def apply_all_proposals(
    branch_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    approver = current_user.get("email", current_user.get("sub", "unknown"))
    manager = BranchEditManager()
    try:
        result = await manager.apply_all_pending(branch_id, approver, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/proposals/{proposal_id}/diff")
async def get_proposal_diff(
    proposal_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    manager = BranchEditManager()
    try:
        diff = await manager.get_diff(proposal_id, db)
        return {"diff": diff}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/branches/{branch_id}/pr")
@limiter.limit("30/minute")
async def create_pr_from_branch(
    branch_id: str,
    payload: PRCreatePayload,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    manager = BranchEditManager()
    try:
        result = await manager.create_pr_from_session(branch_id, payload.title, payload.body, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
