from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import uuid

from app.api.dependencies import get_tenant_db, require_roles
from app.models.hire import JobPosting, Candidate
from app.models.user import User

router = APIRouter()


@router.post("/hire/auto-onboard/{candidate_id}", status_code=status.HTTP_201_CREATED)
async def auto_onboard_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    stage = getattr(candidate, "stage", None)
    if stage != "hired":
        raise HTTPException(status_code=400, detail="Candidate must be in 'hired' stage to auto-onboard")

    first_name = getattr(candidate, "first_name", "") or ""
    last_name = getattr(candidate, "last_name", "") or ""
    email = getattr(candidate, "email", "") or ""
    job_id = getattr(candidate, "job_id", None)

    department = None
    role = "employee"
    if job_id:
        job_result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
        job = job_result.scalar_one_or_none()
        if job:
            department = getattr(job, "department", None)
            role = getattr(job, "employment_type", "employee")

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Employee with this email already exists")

    new_user = User(
        id=uuid.uuid4().hex,
        email=email,
        full_name=f"{first_name} {last_name}".strip() or email,
        department=department,
        role=role,
        hire_date=datetime.now(timezone.utc),
        is_active=True,
        contract_type="Indefinido",
        base_salary=getattr(candidate, "salary_expectation", 0) or 0,
        vacation_allowance=30,
        country="ES",
        timezone="Europe/Madrid",
        currency="EUR",
        locale="es",
    )
    db.add(new_user)

    candidate.stage = "hired"
    setattr(candidate, "onboarded_at", datetime.now(timezone.utc))

    from app.services.it_knowledge_base import ITKnowledgeArticle
    from app.services.self_service import _get_team_members

    checklist_data = [
        {"task_name": "Firmar contrato laboral", "description": "Revisar y firmar el contrato de trabajo", "responsible_role": "employee", "sort_order": 0, "is_required": True},
        {"task_name": "Completar datos personales", "description": "Actualizar dirección, IBAN y contacto de emergencia", "responsible_role": "employee", "sort_order": 1, "is_required": True},
        {"task_name": "Configurar cuentas corporativas", "description": "Crear cuentas de email, Slack, GitHub, etc.", "responsible_role": "it_manager", "sort_order": 2, "is_required": True},
        {"task_name": "Asignar equipo informático", "description": "Preparar y entregar portátil y periféricos", "responsible_role": "it_manager", "sort_order": 3, "is_required": True},
        {"task_name": "Sesión de bienvenida con RRHH", "description": "Primera reunión de onboarding con HR", "responsible_role": "hr_admin", "sort_order": 4, "is_required": True},
        {"task_name": "Reunión con manager", "description": "Primera reunión 1:1 con responsable directo", "responsible_role": "manager", "sort_order": 5, "is_required": True},
        {"task_name": "Formación obligatoria PRL", "description": "Curso de Prevención de Riesgos Laborales", "responsible_role": "employee", "sort_order": 6, "is_required": True},
        {"task_name": "Configurar herramientas de desarrollo", "description": "Instalar IDE, accesos a repositorios y entornos", "responsible_role": "employee", "sort_order": 7, "is_required": False},
    ]

    from app.models.checklist import ActiveChecklist, ChecklistTask
    checklist = ActiveChecklist(
        id=uuid.uuid4().hex,
        user_id=new_user.id,
        status="in_progress",
        progress=0.0,
    )
    db.add(checklist)
    await db.flush()

    for i, task_data in enumerate(checklist_data):
        task = ChecklistTask(
            id=uuid.uuid4().hex,
            checklist_id=checklist.id,
            task_name=task_data["task_name"],
            description=task_data.get("description"),
            responsible_role=task_data["responsible_role"],
            sort_order=task_data["sort_order"],
            is_required=task_data["is_required"],
        )
        db.add(task)

    await db.commit()
    await db.refresh(new_user)

    return {
        "message": "Candidate onboarded successfully",
        "employee_id": new_user.id,
        "employee_name": new_user.full_name,
        "email": new_user.email,
        "checklist_id": checklist.id,
        "checklist_tasks": len(checklist_data),
    }
