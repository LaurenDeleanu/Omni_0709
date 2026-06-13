from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.dependencies import get_tenant_db, require_roles
from app.models.workflow import WorkflowTemplate, UserWorkflow
from app.models.user import User
from app.models.notification import Notification
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

router = APIRouter()

class StepIn(BaseModel):
    id: str
    title: str
    role: str  # employee, hr_admin, etc.

class TemplateCreate(BaseModel):
    name: str
    type: str  # onboarding, offboarding
    steps: List[StepIn]

class TemplateOut(BaseModel):
    id: str
    name: str
    type: str
    steps: List[Dict[str, Any]]

    class Config:
        from_attributes = True

class UserWorkflowOut(BaseModel):
    id: str
    user_id: str
    template_id: str
    status: str
    steps_status: Dict[str, Any]
    created_at: datetime
    template: TemplateOut | None = None

    class Config:
        from_attributes = True

class AssignTemplateIn(BaseModel):
    template_id: str

class GenerateFromTextIn(BaseModel):
    description: str
    name: str

class ValidateDescriptionIn(BaseModel):
    description: str

def get_user_id(current_user: dict) -> str:
    sub = current_user.get("sub", "")
    return sub.split("|")[-1] if "|" in sub else sub

@router.get("/templates", response_model=List[TemplateOut])
async def list_templates(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin", "employee"]))
):
    """Listar todas las plantillas de onboarding/offboarding."""
    result = await db.execute(select(WorkflowTemplate))
    return result.scalars().all()

@router.post("/templates", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_in: TemplateCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """Crear una nueva plantilla de onboarding/offboarding (Solo HR/Sys Admin)."""
    template = WorkflowTemplate(
        id=uuid.uuid4().hex,
        name=template_in.name,
        type=template_in.type,
        steps=[s.model_dump() for s in template_in.steps]
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template

@router.get("/user/{user_id}", response_model=List[UserWorkflowOut])
async def get_user_workflows(
    user_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """Obtener los workflows activos de un usuario."""
    req_user_id = get_user_id(current_user)
    
    # Si no es HR/Admin, el usuario solo puede ver su propio workflow
    if "hr_admin" not in current_user.get("roles", []) and req_user_id != user_id:
        raise HTTPException(status_code=403, detail="No tienes permisos para ver este workflow.")
        
    result = await db.execute(
        select(UserWorkflow)
        .where(UserWorkflow.user_id == user_id)
        .order_by(UserWorkflow.created_at.desc())
    )
    workflows = result.scalars().all()
    
    populated = []
    for w in workflows:
        template_res = await db.execute(select(WorkflowTemplate).where(WorkflowTemplate.id == w.template_id))
        template = template_res.scalar_one_or_none()
        
        populated.append(
            UserWorkflowOut(
                id=w.id,
                user_id=w.user_id,
                template_id=w.template_id,
                status=w.status,
                steps_status=w.steps_status,
                created_at=w.created_at,
                template=TemplateOut.model_validate(template) if template else None
            )
        )
    return populated

@router.post("/user/{user_id}/assign", response_model=UserWorkflowOut, status_code=status.HTTP_201_CREATED)
async def assign_workflow_to_user(
    user_id: str,
    payload: AssignTemplateIn,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin"]))
):
    """Asignar un checklist de Onboarding/Offboarding a un empleado (Solo HR Admin)."""
    # Verificar plantilla
    t_res = await db.execute(select(WorkflowTemplate).where(WorkflowTemplate.id == payload.template_id))
    template = t_res.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
        
    # Verificar usuario
    u_res = await db.execute(select(User).where(User.id == user_id))
    user = u_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    # Crear workflow del usuario con steps inicializados
    steps_status = {}
    for step in template.steps:
        steps_status[step["id"]] = {
            "completed": False,
            "completed_at": None,
            "completed_by": None
        }
        
    user_workflow = UserWorkflow(
        id=uuid.uuid4().hex,
        user_id=user_id,
        template_id=payload.template_id,
        status="in_progress",
        steps_status=steps_status
    )
    db.add(user_workflow)
    
    # Notificación automática
    notification = Notification(
        id=uuid.uuid4().hex,
        user_id=user_id,
        title=f"📋 Nuevo Workflow Asignado: {template.name}",
        message=f"Se te ha asignado el checklist '{template.name}'. Por favor, completa las tareas de tu lista.",
        type="task",
        is_read=False
    )
    db.add(notification)
    
    await db.commit()
    await db.refresh(user_workflow)
    
    return UserWorkflowOut(
        id=user_workflow.id,
        user_id=user_workflow.user_id,
        template_id=user_workflow.template_id,
        status=user_workflow.status,
        steps_status=user_workflow.steps_status,
        created_at=user_workflow.created_at,
        template=TemplateOut.model_validate(template)
    )

@router.post("/user/{user_id}/steps/{step_id}/toggle", response_model=UserWorkflowOut)
async def toggle_step(
    user_id: str,
    step_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """Marcar/Desmarcar una tarea del checklist de onboarding/offboarding."""
    req_user_id = get_user_id(current_user)
    
    # Buscar el workflow activo para este usuario
    result = await db.execute(
        select(UserWorkflow)
        .where(UserWorkflow.user_id == user_id, UserWorkflow.status == "in_progress")
        .order_by(UserWorkflow.created_at.desc())
    )
    workflow = result.scalars().first()
    if not workflow:
        raise HTTPException(status_code=404, detail="No se encontró ningún workflow activo para el usuario.")
        
    # Buscar plantilla para verificar el rol del paso
    t_res = await db.execute(select(WorkflowTemplate).where(WorkflowTemplate.id == workflow.template_id))
    template = t_res.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
        
    # Encontrar paso
    step = next((s for s in template.steps if s["id"] == step_id), None)
    if not step:
        raise HTTPException(status_code=404, detail="Paso del checklist no encontrado.")
        
    # Si no es HR y el paso requiere rol de HR, denegar
    if step["role"] != "employee" and "hr_admin" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="Este paso solo puede ser completado por el equipo de RRHH.")
        
    # Si no es HR y está editando el workflow de otro, denegar
    if "hr_admin" not in current_user.get("roles", []) and req_user_id != user_id:
        raise HTTPException(status_code=403, detail="No puedes modificar la lista de otro empleado.")

    # Modificar steps_status
    steps_status = dict(workflow.steps_status)
    current_state = steps_status.get(step_id, {"completed": False})
    
    if current_state.get("completed", False):
        steps_status[step_id] = {
            "completed": False,
            "completed_at": None,
            "completed_by": None
        }
    else:
        steps_status[step_id] = {
            "completed": True,
            "completed_at": datetime.now().isoformat(),
            "completed_by": req_user_id
        }
        
    # Verificar si todas están completadas para actualizar status de workflow
    all_completed = True
    for s_id, s_val in steps_status.items():
        if not s_val.get("completed", False):
            all_completed = False
            break
            
    workflow.steps_status = steps_status
    if all_completed:
        workflow.status = "completed"
        # Notificación automática de éxito
        notification = Notification(
            id=uuid.uuid4().hex,
            user_id=user_id,
            title=f"🏆 Checklist Completado: {template.name}",
            message=f"¡Felicidades! Has completado con éxito todos los pasos del workflow '{template.name}'.",
            type="system",
            is_read=False
        )
        db.add(notification)
        
    # Para evitar mutabilidad no detectada en SQLAlchemy JSON fields, forzar asignación
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(workflow, "steps_status")
    
    await db.commit()
    await db.refresh(workflow)
    
    return UserWorkflowOut(
        id=workflow.id,
        user_id=workflow.user_id,
        template_id=workflow.template_id,
        status=workflow.status,
        steps_status=workflow.steps_status,
        created_at=workflow.created_at,
        template=TemplateOut.model_validate(template)
    )


@router.post("/validate-description")
async def validate_workflow_description(
    payload: ValidateDescriptionIn,
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """Validate whether a natural language description is sufficient to generate a workflow."""
    from app.services.nl_workflow_builder import validate_workflow_description as validate_fn
    return await validate_fn(description=payload.description)


@router.post("/generate-from-text/preview")
async def preview_workflow_from_text(
    payload: GenerateFromTextIn,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """Generate a workflow definition from natural language without saving it."""
    from app.services.nl_workflow_builder import generate_workflow_from_text
    return await generate_workflow_from_text(
        description=payload.description,
        tenant_id="",
        db=db,
    )


@router.post("/generate-from-text", status_code=status.HTTP_201_CREATED)
async def create_workflow_from_text(
    payload: GenerateFromTextIn,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """Generate a complete workflow from natural language description and create it in the database."""
    from app.services.nl_workflow_builder import create_workflow_from_nl
    user_id = get_user_id(current_user)
    result = await create_workflow_from_nl(
        description=payload.description,
        name=payload.name,
        user_id=user_id,
        tenant_id="",
        db=db,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/{workflow_id}/suggest-improvements")
async def suggest_workflow_improvements(
    workflow_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """Analyze an existing workflow and suggest optimizations."""
    from app.services.nl_workflow_builder import suggest_workflow_improvements as suggest_fn
    result = await suggest_fn(workflow_id=workflow_id, db=db)
    if result.get("error") and not result.get("suggestions"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/templates")
async def list_workflow_templates(category: str = ""):
    from app.services.workflow_templates import list_templates, get_categories
    return {"templates": list_templates(category), "categories": get_categories()}


@router.get("/templates/{template_id}")
async def get_workflow_template(template_id: str):
    from app.services.workflow_templates import get_template
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template
