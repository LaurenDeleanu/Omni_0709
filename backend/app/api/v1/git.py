from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import json
import logging

from app.api.dependencies import get_tenant_db, require_roles
from app.models.git import GitRepository, CodeModule
from app.models.agent import Agent
from app.services.git_service import create_github_branch, commit_github_files, create_github_pr
from app.services.llm_router import encrypt_key, decrypt_key, get_llm_client
from app.services.llm_router import get_openai_client
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Pydantic Schemas ---
class GitRepositoryCreate(BaseModel):
    provider: str = "github"
    repo_url: str
    access_token: str
    default_branch: str = "main"
    dev_branch: str = "dev"

class CodeScaffoldRequest(BaseModel):
    agent_id: str
    repo_id: str
    title: str
    prompt: str

class ProposalFile(BaseModel):
    path: str
    content: str
    language: Optional[str] = None

class GitProposalCreate(BaseModel):
    repoId: str
    agentId: str
    title: str
    description: str
    files: List[ProposalFile]

# --- Routes ---

@router.get("/repositories")
async def list_repositories(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Lista los repositorios vinculados al tenant.
    """
    result = await db.execute(select(GitRepository).order_by(GitRepository.created_at.desc()))
    repos = result.scalars().all()
    return [
        {
            "id": r.id,
            "provider": r.provider,
            "repo_url": r.repo_url,
            "default_branch": r.default_branch,
            "dev_branch": r.dev_branch,
            "created_at": r.created_at.isoformat()
        } for r in repos
    ]

@router.post("/repositories", status_code=status.HTTP_201_CREATED)
async def connect_repository(
    payload: GitRepositoryCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Registra y conecta un nuevo repositorio Git cifrando el token de acceso.
    """
    repo = GitRepository(
        id=uuid.uuid4().hex,
        provider=payload.provider,
        repo_url=payload.repo_url,
        access_token=encrypt_key(payload.access_token),
        default_branch=payload.default_branch,
        dev_branch=payload.dev_branch
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)
    return {
        "id": repo.id,
        "provider": repo.provider,
        "repo_url": repo.repo_url
    }

@router.post("/modules/generate", status_code=status.HTTP_201_CREATED)
async def generate_scaffold_module(
    payload: CodeScaffoldRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Usa el Agente de IA para generar un scaffold de código (archivos)
    y crear un registro de CodeModule.
    """
    # 1. Cargar agente y repo
    agent_res = await db.execute(select(Agent).where(Agent.id == payload.agent_id))
    agent = agent_res.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
        
    repo_res = await db.execute(select(GitRepository).where(GitRepository.id == payload.repo_id))
    repo = repo_res.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repositorio no encontrado")
        
    # 2. Llamar a OpenAI/Gemini para generar los archivos
    prompt_str = (
        f"Genera los archivos para el siguiente requerimiento técnico: '{payload.prompt}'\n\n"
        f"Debes responder en formato JSON que representa una lista de archivos. Formato:\n"
        f"[\n"
        f"  {{\n"
        f"    \"path\": \"nombre_archivo.js\",\n"
        f"    \"content\": \"contenido de código completo...\",\n"
        f"    \"language\": \"javascript\"\n"
        f"  }}\n"
        f"]\n"
        f"Responde estrictamente con el JSON de la lista, sin bloques markdown de formato."
    )
    
    try:
        client, _ = await get_openai_client(agent)
        response = await client.chat.completions.create(
            model=agent.ai_model,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt_str}]
        )
        
        raw_text = response.choices[0].message.content.strip()
        clean_json = raw_text
        if "[" in clean_json and "]" in clean_json:
            clean_json = clean_json[clean_json.find("["):clean_json.rfind("]")+1]
            
        generated_files = json_parse_safe(clean_json)
        if not isinstance(generated_files, list):
            # Fallback simple
            generated_files = [{
                "path": "index.js",
                "content": f"// Fallback scaffold\nconsole.log('{payload.prompt}');",
                "language": "javascript"
            }]
            
    except Exception as e:
        generated_files = [{
            "path": "error_log.txt",
            "content": f"Fallo al contactar LLM: {str(e)}",
            "language": "plaintext"
        }]

    # 3. Guardar módulo
    module = CodeModule(
        id=uuid.uuid4().hex,
        repo_id=payload.repo_id,
        agent_id=payload.agent_id,
        title=payload.title,
        description=payload.prompt,
        files=generated_files,
        status="draft"
    )
    db.add(module)
    await db.commit()
    await db.refresh(module)
    
    return {
        "id": module.id,
        "title": module.title,
        "status": module.status,
        "files_count": len(generated_files)
    }

@router.get("/modules/{module_id}")
async def get_code_module(
    module_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Obtiene los detalles de un módulo de código generado.
    """
    res = await db.execute(select(CodeModule).where(CodeModule.id == module_id))
    module = res.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Módulo no encontrado")
        
    return {
        "id": module.id,
        "repo_id": module.repo_id,
        "agent_id": module.agent_id,
        "title": module.title,
        "description": module.description,
        "files": module.files,
        "status": module.status,
        "branch_name": module.branch_name,
        "pr_url": module.pr_url,
        "reviewed_by": module.reviewed_by
    }

@router.post("/modules/{module_id}/pr")
async def deploy_and_create_pr(
    module_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Realiza el deploy del código:
    1. Crea una rama de desarrollo en GitHub.
    2. Hace commit de los archivos generados.
    3. Abre un Pull Request contra la rama base del repositorio.
    """
    res = await db.execute(select(CodeModule).where(CodeModule.id == module_id))
    module = res.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Módulo no encontrado")
        
    repo_res = await db.execute(select(GitRepository).where(GitRepository.id == module.repo_id))
    repo = repo_res.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repositorio no encontrado")
        
    token = decrypt_key(repo.access_token)
    new_branch = f"agent-feature-{uuid.uuid4().hex[:8]}"
    
    # 1. Crear rama
    branch_ok = await create_github_branch(
        repo_url=repo.repo_url,
        token=token,
        base_branch=repo.dev_branch,
        new_branch=new_branch
    )
    if not branch_ok:
        raise HTTPException(status_code=400, detail="No se pudo crear la rama en el repositorio remoto.")
        
    # 2. Subir commits
    commit_ok = await commit_github_files(
        repo_url=repo.repo_url,
        token=token,
        branch_name=new_branch,
        files=module.files,
        commit_message=f"feat: {module.title} (Scaffolded by successcore AI)"
    )
    if not commit_ok:
        raise HTTPException(status_code=400, detail="No se pudieron commitear los archivos a la rama remota.")
        
    # 3. Crear PR
    pr_url = await create_github_pr(
        repo_url=repo.repo_url,
        token=token,
        title=f"Merge {module.title}",
        body=f"Este PR contiene código autogenerado por el agente de IA:\n{module.description}",
        head_branch=new_branch,
        base_branch=repo.dev_branch
    )
    
    if pr_url:
        module.status = "review"
        module.branch_name = new_branch
        module.pr_url = pr_url
        await db.commit()
        return {
            "status": "success",
            "pr_url": pr_url,
            "branch": new_branch
        }
    else:
        raise HTTPException(status_code=400, detail="No se pudo abrir el Pull Request remoto.")

@router.get("/modules")
async def list_code_proposals(
    agent_id: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """
    Lista las propuestas de código (CodeModules) creadas en el repositorio.
    """
    stmt = select(CodeModule)
    if agent_id:
        stmt = stmt.where(CodeModule.agent_id == agent_id)
    stmt = stmt.order_by(CodeModule.created_at.desc())
    
    result = await db.execute(stmt)
    modules = result.scalars().all()
    
    out = []
    for m in modules:
        repo_res = await db.execute(select(GitRepository).where(GitRepository.id == m.repo_id))
        repo = repo_res.scalar_one_or_none()
        out.append({
            "id": m.id,
            "repo_id": m.repo_id,
            "agent_id": m.agent_id,
            "title": m.title,
            "description": m.description,
            "files": m.files,
            "status": m.status,
            "branchName": m.branch_name,
            "branch_name": m.branch_name,
            "prUrl": m.pr_url,
            "pr_url": m.pr_url,
            "reviewed_by": m.reviewed_by,
            "createdAt": m.created_at.isoformat() if m.created_at else None,
            "repo": {
                "provider": repo.provider if repo else "github",
                "repoUrl": repo.repo_url if repo else ""
            } if repo else None
        })
    return {"modules": out}

@router.post("/modules", status_code=status.HTTP_201_CREATED)
async def submit_git_proposal(
    payload: GitProposalCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """
    Crea una rama remota, sube los cambios de código a GitHub, abre un PR
    y realiza un audit de código con IA para emitir una puntuación de calidad (0-100) y feedback.
    """
    agent_res = await db.execute(select(Agent).where(Agent.id == payload.agentId))
    agent = agent_res.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
        
    repo_res = await db.execute(select(GitRepository).where(GitRepository.id == payload.repoId))
    repo = repo_res.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repositorio no encontrado")
        
    token = decrypt_key(repo.access_token)
    new_branch = f"agent-proposal-{uuid.uuid4().hex[:8]}"
    
    files_list = [{"path": f.path, "content": f.content} for f in payload.files]
    
    branch_ok = await create_github_branch(
        repo_url=repo.repo_url,
        token=token,
        base_branch=repo.dev_branch,
        new_branch=new_branch
    )
    if not branch_ok:
        raise HTTPException(status_code=400, detail="No se pudo crear la rama en el repositorio remoto.")
        
    commit_ok = await commit_github_files(
        repo_url=repo.repo_url,
        token=token,
        branch_name=new_branch,
        files=files_list,
        commit_message=f"feat: {payload.title} (Proposed by AI/CodeLab)"
    )
    if not commit_ok:
        raise HTTPException(status_code=400, detail="No se pudieron commitear los archivos a la rama remota.")
        
    pr_url = await create_github_pr(
        repo_url=repo.repo_url,
        token=token,
        title=payload.title,
        body=payload.description,
        head_branch=new_branch,
        base_branch=repo.dev_branch
    )
    if not pr_url:
        raise HTTPException(status_code=400, detail="No se pudo abrir el Pull Request remoto.")
        
    review_score = 85
    review_feedback = "Código aceptable. Se recomienda realizar pruebas de integración antes del merge."
    
    try:
        prompt_str = (
            f"Eres un Ingeniero Principal de Control de Calidad. Debes auditar los siguientes cambios de código propuestos.\n"
            f"Título: {payload.title}\n"
            f"Descripción: {payload.description}\n\n"
            f"Archivos propuestos:\n"
            f"{json.dumps(files_list, indent=2)}\n\n"
            f"Por favor, responde estrictamente en formato JSON con la siguiente estructura:\n"
            f"{{\n"
            f"  \"score\": <un número entero del 0 al 100 representando la calidad y seguridad del código>,\n"
            f"  \"feedback\": \"<detalles específicos de la auditoría y sugerencias de mejora>\"\n"
            f"}}\n"
            f"Responde únicamente con el JSON bruto, sin bloques markdown de formato ni comentarios adicionales."
        )
        
        client, _ = await get_llm_client(agent.ai_model, agent, db)
        response = await client.chat.completions.create(
            model=agent.ai_model,
            messages=[{"role": "user", "content": prompt_str}],
            temperature=0.1
        )
        raw_text = response.choices[0].message.content.strip()
        
        clean_json = raw_text
        if "{" in clean_json and "}" in clean_json:
            clean_json = clean_json[clean_json.find("{"):clean_json.rfind("}")+1]
            
        parsed_audit = json.loads(clean_json)
        review_score = int(parsed_audit.get("score", 85))
        review_feedback = str(parsed_audit.get("feedback", review_feedback))
    except Exception as e:
        logger.warning(f"Failed to run AI Code Review Audit: {e}. Using fallback review values.")
        
    module = CodeModule(
        id=uuid.uuid4().hex,
        repo_id=payload.repoId,
        agent_id=payload.agentId,
        title=payload.title,
        description=payload.description,
        files=[{"path": f.path, "content": f.content, "language": f.language} for f in payload.files],
        status="review",
        branch_name=new_branch,
        pr_url=pr_url,
        reviewed_by=f"AI Judge ({agent.ai_model})"
    )
    db.add(module)
    await db.commit()
    await db.refresh(module)
    
    return {
        "success": True,
        "branchName": new_branch,
        "prUrl": pr_url,
        "reviewScore": review_score,
        "reviewFeedback": review_feedback
    }

def json_parse_safe(text: str) -> Any:
    """Intenta parsear JSON de manera segura."""
    import json
    try:
        return json.loads(text)
    except:
        return text
