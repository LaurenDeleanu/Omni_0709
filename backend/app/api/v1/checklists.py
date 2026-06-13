from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid

from app.api.dependencies import get_tenant_db, get_current_user, require_roles
from app.models.checklist import (
    ChecklistTemplate,
    ChecklistTemplateTask,
    ActiveChecklist,
    ChecklistTask,
)
from app.models.user import User

router = APIRouter()


class TemplateTaskSchema(BaseModel):
    task_name: str
    description: Optional[str] = None
    responsible_role: str = "employee"
    sort_order: int = 0
    is_required: bool = True

    model_config = {"from_attributes": True}


class ChecklistTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str = "onboarding"
    tasks: List[TemplateTaskSchema] = []


class ChecklistTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ChecklistTemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: str
    is_active: bool
    task_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChecklistTemplateDetailResponse(ChecklistTemplateResponse):
    tasks: List[TemplateTaskSchema] = []


class AssignChecklistRequest(BaseModel):
    template_id: str
    user_id: str
    due_date: Optional[str] = None


class ChecklistTaskToggle(BaseModel):
    completed: bool
    notes: Optional[str] = None


class ChecklistTaskResponse(BaseModel):
    id: str
    checklist_id: str
    task_name: str
    description: Optional[str] = None
    responsible_role: str
    sort_order: int
    is_required: bool
    is_completed: bool
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class ActiveChecklistResponse(BaseModel):
    id: str
    template_id: Optional[str] = None
    user_id: str
    assigned_by: Optional[str] = None
    status: str
    progress: float
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    tasks: List[ChecklistTaskResponse] = []

    model_config = {"from_attributes": True}


class EmployeeHubResponse(BaseModel):
    user_id: str
    full_name: str
    email: str
    department: Optional[str] = None
    role: str
    hire_date: Optional[str] = None
    contract_type: Optional[str] = None
    base_salary: Optional[float] = None
    vacation_allowance: int = 0
    vacation_used: int = 0
    vacation_remaining: int = 0
    manager_name: Optional[str] = None
    team_size: int = 0
    active_checklists: int = 0
    completed_checklists: int = 0
    recent_payslips: int = 0


def _get_user_id(user_payload: dict) -> str:
    sub = user_payload.get("sub", "")
    if "|" in sub:
        return sub.split("|")[-1]
    return sub or "unknown"


# ── Templates CRUD ──

@router.get("/checklist-templates", response_model=List[ChecklistTemplateResponse])
async def list_templates(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    result = await db.execute(
        select(ChecklistTemplate).order_by(ChecklistTemplate.created_at.desc())
    )
    templates = result.scalars().all()
    items = []
    for t in templates:
        task_count_result = await db.execute(
            select(func.count()).select_from(ChecklistTemplateTask).where(ChecklistTemplateTask.template_id == t.id)
        )
        task_count = task_count_result.scalar() or 0
        items.append(ChecklistTemplateResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            category=t.category,
            is_active=t.is_active,
            task_count=task_count,
            created_at=t.created_at,
            updated_at=t.updated_at,
        ))
    return items


@router.post("/checklist-templates", response_model=ChecklistTemplateDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: ChecklistTemplateCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    template = ChecklistTemplate(
        id=uuid.uuid4().hex,
        name=data.name,
        description=data.description,
        category=data.category,
    )
    db.add(template)
    await db.flush()

    tasks = []
    for i, t in enumerate(data.tasks):
        task = ChecklistTemplateTask(
            id=uuid.uuid4().hex,
            template_id=template.id,
            task_name=t.task_name,
            description=t.description,
            responsible_role=t.responsible_role,
            sort_order=t.sort_order or i,
            is_required=t.is_required,
        )
        db.add(task)
        tasks.append(TemplateTaskSchema(
            task_name=task.task_name,
            description=task.description,
            responsible_role=task.responsible_role,
            sort_order=task.sort_order,
            is_required=task.is_required,
        ))

    await db.commit()

    return ChecklistTemplateDetailResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category,
        is_active=template.is_active,
        task_count=len(tasks),
        tasks=tasks,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.get("/checklist-templates/{template_id}", response_model=ChecklistTemplateDetailResponse)
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    result = await db.execute(select(ChecklistTemplate).where(ChecklistTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    tasks_result = await db.execute(
        select(ChecklistTemplateTask).where(ChecklistTemplateTask.template_id == template.id).order_by(ChecklistTemplateTask.sort_order)
    )
    tasks = tasks_result.scalars().all()

    return ChecklistTemplateDetailResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category,
        is_active=template.is_active,
        task_count=len(tasks),
        tasks=[TemplateTaskSchema(
            task_name=t.task_name,
            description=t.description,
            responsible_role=t.responsible_role,
            sort_order=t.sort_order,
            is_required=t.is_required,
        ) for t in tasks],
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.delete("/checklist-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    result = await db.execute(select(ChecklistTemplate).where(ChecklistTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.delete(template)
    await db.commit()
    return None


# ── Active Checklists ──

@router.post("/assign-checklist", response_model=ActiveChecklistResponse, status_code=status.HTTP_201_CREATED)
async def assign_checklist(
    data: AssignChecklistRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    result = await db.execute(select(ChecklistTemplate).where(ChecklistTemplate.id == data.template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    user_result = await db.execute(select(User).where(User.id == data.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    checklist = ActiveChecklist(
        id=uuid.uuid4().hex,
        template_id=template.id,
        user_id=data.user_id,
        assigned_by=_get_user_id(current_user),
        status="in_progress",
        progress=0.0,
        due_date=datetime.fromisoformat(data.due_date) if data.due_date else None,
    )
    db.add(checklist)
    await db.flush()

    tasks_result = await db.execute(
        select(ChecklistTemplateTask).where(ChecklistTemplateTask.template_id == template.id).order_by(ChecklistTemplateTask.sort_order)
    )
    template_tasks = tasks_result.scalars().all()

    task_responses = []
    for tt in template_tasks:
        task = ChecklistTask(
            id=uuid.uuid4().hex,
            checklist_id=checklist.id,
            task_name=tt.task_name,
            description=tt.description,
            responsible_role=tt.responsible_role,
            sort_order=tt.sort_order,
            is_required=tt.is_required,
        )
        db.add(task)
        task_responses.append(ChecklistTaskResponse(
            id=task.id,
            checklist_id=checklist.id,
            task_name=task.task_name,
            description=task.description,
            responsible_role=task.responsible_role,
            sort_order=task.sort_order,
            is_required=task.is_required,
            is_completed=False,
            completed_at=None,
            completed_by=None,
            notes=None,
        ))

    await db.commit()

    return ActiveChecklistResponse(
        id=checklist.id,
        template_id=checklist.template_id,
        user_id=checklist.user_id,
        assigned_by=checklist.assigned_by,
        status=checklist.status,
        progress=checklist.progress,
        due_date=checklist.due_date,
        created_at=checklist.created_at,
        updated_at=checklist.updated_at,
        tasks=task_responses,
    )


@router.get("/my-checklists", response_model=List[ActiveChecklistResponse])
async def get_my_checklists(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = _get_user_id(current_user)
    result = await db.execute(
        select(ActiveChecklist).where(ActiveChecklist.user_id == user_id).order_by(ActiveChecklist.created_at.desc())
    )
    checklists = result.scalars().all()

    items = []
    for ck in checklists:
        tasks_result = await db.execute(
            select(ChecklistTask).where(ChecklistTask.checklist_id == ck.id).order_by(ChecklistTask.sort_order)
        )
        tasks = tasks_result.scalars().all()
        items.append(ActiveChecklistResponse(
            id=ck.id,
            template_id=ck.template_id,
            user_id=ck.user_id,
            assigned_by=ck.assigned_by,
            status=ck.status,
            progress=ck.progress,
            due_date=ck.due_date,
            created_at=ck.created_at,
            updated_at=ck.updated_at,
            tasks=[ChecklistTaskResponse(
                id=t.id,
                checklist_id=t.checklist_id,
                task_name=t.task_name,
                description=t.description,
                responsible_role=t.responsible_role,
                sort_order=t.sort_order,
                is_required=t.is_required,
                is_completed=t.is_completed,
                completed_at=t.completed_at,
                completed_by=t.completed_by,
                notes=t.notes,
            ) for t in tasks],
        ))
    return items


@router.patch("/checklist-tasks/{task_id}", response_model=ChecklistTaskResponse)
async def toggle_checklist_task(
    task_id: str,
    data: ChecklistTaskToggle,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    result = await db.execute(select(ChecklistTask).where(ChecklistTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    user_id = _get_user_id(current_user)
    task.is_completed = data.completed
    task.completed_at = datetime.now(timezone.utc) if data.completed else None
    task.completed_by = user_id if data.completed else None
    if data.notes is not None:
        task.notes = data.notes

    await db.flush()

    checklist_result = await db.execute(select(ActiveChecklist).where(ActiveChecklist.id == task.checklist_id))
    checklist = checklist_result.scalar_one_or_none()
    if checklist:
        total = await db.scalar(select(func.count()).select_from(ChecklistTask).where(ChecklistTask.checklist_id == checklist.id))
        completed = await db.scalar(select(func.count()).select_from(ChecklistTask).where(
            ChecklistTask.checklist_id == checklist.id, ChecklistTask.is_completed == True
        ))
        checklist.progress = (completed / total * 100) if total else 0
        checklist.status = "completed" if checklist.progress >= 100 else "in_progress"

    await db.commit()

    return ChecklistTaskResponse(
        id=task.id,
        checklist_id=task.checklist_id,
        task_name=task.task_name,
        description=task.description,
        responsible_role=task.responsible_role,
        sort_order=task.sort_order,
        is_required=task.is_required,
        is_completed=task.is_completed,
        completed_at=task.completed_at,
        completed_by=task.completed_by,
        notes=task.notes,
    )


@router.get("/employee-hub", response_model=EmployeeHubResponse)
async def get_employee_hub(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = _get_user_id(current_user)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    manager_name = None
    if user.manager_id:
        mgr_result = await db.execute(select(User.full_name).where(User.id == user.manager_id))
        manager_name = mgr_result.scalar_one_or_none()

    team_size = 0
    if user.role in ("hr_admin", "manager"):
        team_result = await db.scalar(
            select(func.count()).select_from(User).where(User.manager_id == user_id, User.is_active == True)
        )
        team_size = team_result or 0

    vacation_used_result = await db.scalar(
        select(func.count()).select_from(ActiveChecklist).where(ActiveChecklist.user_id == user_id)
    )
    active_checklists = vacation_used_result or 0

    completed_result = await db.scalar(
        select(func.count()).select_from(ActiveChecklist).where(
            ActiveChecklist.user_id == user_id, ActiveChecklist.status == "completed"
        )
    )
    completed_checklists = completed_result or 0

    vacation_used = max(0, 22 - ((user.vacation_allowance or 30) - 8)) if (user.vacation_allowance or 30) > 22 else 0
    vacation_remaining = (user.vacation_allowance or 30) - vacation_used

    return EmployeeHubResponse(
        user_id=user.id,
        full_name=user.full_name or user.email,
        email=user.email,
        department=user.department,
        role=user.role,
        hire_date=user.hire_date.isoformat() if user.hire_date else None,
        contract_type=user.contract_type,
        base_salary=user.base_salary,
        vacation_allowance=user.vacation_allowance or 30,
        vacation_used=vacation_used,
        vacation_remaining=vacation_remaining,
        manager_name=manager_name,
        team_size=team_size,
        active_checklists=active_checklists,
        completed_checklists=completed_checklists,
        recent_payslips=3,
    )
