from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from typing import List, Optional
from datetime import datetime, timezone, date
import uuid

from app.api.dependencies import get_tenant_db, get_current_user, require_roles
from app.models.calendar import VacationRequest, Meeting, Task
from app.models.notification import Notification
from app.schemas.calendar import (
    VacationCreate, VacationReview, VacationResponse,
    MeetingCreate, MeetingUpdate, MeetingResponse,
    TaskCreate, TaskUpdate, TaskResponse,
    CalendarEvent,
)

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_user_id(current_user: dict) -> str:
    """Extraer el sub (user id) del token JWT y limpiar el prefijo de proveedor."""
    sub = current_user.get("sub", "unknown")
    return sub.split("|")[-1] if "|" in sub else sub


def _get_user_roles(current_user: dict) -> list:
    """Extraer roles del token, misma lógica que require_roles."""
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    roles = app_metadata.get("roles", [])
    if not roles:
        roles = current_user.get("https://successcore.com/roles", [])
    if not roles:
        roles = current_user.get("roles", [])
    if not roles:
        roles = ["hr_admin"]
    return roles


# ═══════════════════════════════════════════════════════════════════════════════
#  VACACIONES
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/vacations", response_model=List[VacationResponse])
async def list_vacations(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Listar solicitudes de vacaciones. HR admin ve todas; employee solo las suyas."""
    roles = _get_user_roles(current_user)
    user_id = _get_user_id(current_user)

    query = select(VacationRequest).order_by(VacationRequest.created_at.desc())
    if "hr_admin" not in roles and "super_admin" not in roles:
        query = query.where(VacationRequest.user_id == user_id)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/vacations", response_model=VacationResponse, status_code=status.HTTP_201_CREATED)
async def create_vacation(
    data: VacationCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Crear una solicitud de vacaciones."""
    if data.end_date < data.start_date:
        raise HTTPException(status_code=400, detail="La fecha de fin no puede ser anterior a la de inicio.")

    vacation = VacationRequest(
        id=uuid.uuid4().hex,
        user_id=_get_user_id(current_user),
        **data.model_dump(),
    )
    db.add(vacation)
    
    # Crear notificación automática
    notification = Notification(
        id=uuid.uuid4().hex,
        user_id=vacation.user_id,
        title="✈️ Solicitud de vacaciones enviada",
        message=f"Tu solicitud de vacaciones del {data.start_date} al {data.end_date} ha sido registrada y está pendiente de revisión.",
        type="vacation",
        is_read=False
    )
    db.add(notification)
    
    await db.commit()
    await db.refresh(vacation)
    return vacation


@router.patch("/vacations/{vacation_id}/review", response_model=VacationResponse)
async def review_vacation(
    vacation_id: str,
    review: VacationReview,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"])),
    current_user: dict = Depends(get_current_user),
):
    """Aprobar o rechazar una solicitud de vacaciones (solo hr_admin)."""
    if review.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Estado debe ser 'approved' o 'rejected'.")

    result = await db.execute(select(VacationRequest).where(VacationRequest.id == vacation_id))
    vacation = result.scalar_one_or_none()
    if not vacation:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")

    vacation.status = review.status
    vacation.reviewed_by = _get_user_id(current_user)
    vacation.reviewed_at = datetime.now(timezone.utc)

    # Crear notificación automática sobre la resolución
    status_label = "aprobada" if review.status == "approved" else "rechazada"
    notification = Notification(
        id=uuid.uuid4().hex,
        user_id=vacation.user_id,
        title=f"✈️ Solicitud de vacaciones {status_label}",
        message=f"Tu solicitud de vacaciones del {vacation.start_date} al {vacation.end_date} ha sido {status_label}.",
        type="vacation",
        is_read=False
    )
    db.add(notification)

    try:
        from app.services.event_publisher import publish_vacation_event
        await publish_vacation_event(db, vacation.id, vacation.user_id, str(vacation.start_date), str(vacation.end_date), review.status, "acme_corp")
    except Exception:
        pass

    await db.commit()
    await db.refresh(vacation)
    return vacation


# ═══════════════════════════════════════════════════════════════════════════════
#  REUNIONES
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/meetings", response_model=List[MeetingResponse])
async def list_meetings(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Listar reuniones donde el usuario es organizador o asistente."""
    roles = _get_user_roles(current_user)
    user_id = _get_user_id(current_user)
    query = select(Meeting).order_by(Meeting.start_datetime.desc())
    if "hr_admin" not in roles:
        query = query.where(
            or_(Meeting.organizer_id == user_id, Meeting.attendees.contains([user_id]))
        )
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/meetings", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    data: MeetingCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Crear una reunión."""
    meeting = Meeting(
        id=uuid.uuid4().hex,
        organizer_id=_get_user_id(current_user),
        **data.model_dump(),
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)
    return meeting


@router.put("/meetings/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: str,
    data: MeetingUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Actualizar una reunión."""
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Reunión no encontrada.")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(meeting, field, value)

    await db.commit()
    await db.refresh(meeting)
    return meeting


@router.delete("/meetings/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(
    meeting_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Eliminar una reunión."""
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Reunión no encontrada.")

    await db.delete(meeting)
    await db.commit()
    return None


# ═══════════════════════════════════════════════════════════════════════════════
#  TAREAS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Listar tareas asignadas al usuario o creadas por él."""
    user_id = _get_user_id(current_user)
    roles = _get_user_roles(current_user)

    query = select(Task).order_by(Task.due_date.asc().nullslast(), Task.created_at.desc())
    if "hr_admin" not in roles:
        query = query.where(
            or_(Task.assigned_to == user_id, Task.created_by == user_id)
        )

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Crear una tarea."""
    task = Task(
        id=uuid.uuid4().hex,
        created_by=_get_user_id(current_user),
        **data.model_dump(),
    )
    db.add(task)
    
    # Notificar si se asigna a otro usuario
    if task.assigned_to != task.created_by:
        notification = Notification(
            id=uuid.uuid4().hex,
            user_id=task.assigned_to,
            title="📋 Nueva tarea asignada",
            message=f"Se te ha asignado la tarea: \"{task.title}\" con prioridad {task.priority}.",
            type="task",
            is_read=False
        )
        db.add(notification)
        
    await db.commit()
    await db.refresh(task)
    return task


@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Actualizar una tarea (estado, prioridad, etc.)."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada.")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Eliminar una tarea."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada.")

    await db.delete(task)
    await db.commit()
    return None


# ═══════════════════════════════════════════════════════════════════════════════
#  CALENDARIO UNIFICADO
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/events", response_model=List[CalendarEvent])
async def get_calendar_events(
    month: Optional[str] = Query(None, description="Formato YYYY-MM para filtrar por mes"),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Devuelve todos los eventos (vacaciones + reuniones + tareas) unificados
    para renderizar en el calendario. Opcionalmente filtra por mes.
    HR admin ve todo; employee ve solo sus propios eventos.
    """
    roles = _get_user_roles(current_user)
    user_id = _get_user_id(current_user)
    is_admin = "hr_admin" in roles
    events: List[CalendarEvent] = []

    # ── Vacaciones ────────────────────────────────────────────────────────────
    vac_query = select(VacationRequest).order_by(VacationRequest.start_date)
    if not is_admin:
        vac_query = vac_query.where(VacationRequest.user_id == user_id)
    vac_result = await db.execute(vac_query)
    for v in vac_result.scalars().all():
        events.append(CalendarEvent(
            id=v.id,
            type="vacation",
            title=f"Vacaciones — {v.status}",
            start=v.start_date.isoformat(),
            end=v.end_date.isoformat(),
            status=v.status,
            extra={
                "user_id": v.user_id,
                "reason": v.reason,
                "absence_type": getattr(v, "absence_type", "vacation"),
                "document_path": getattr(v, "document_path", None)
            },
        ))

    # ── Reuniones ─────────────────────────────────────────────────────────────
    meet_query = select(Meeting).order_by(Meeting.start_datetime)
    if not is_admin:
        meet_query = meet_query.where(
            or_(Meeting.organizer_id == user_id, Meeting.attendees.contains([user_id]))
        )
    meet_result = await db.execute(meet_query)
    for m in meet_result.scalars().all():
        events.append(CalendarEvent(
            id=m.id,
            type="meeting",
            title=m.title,
            start=m.start_datetime.isoformat(),
            end=m.end_datetime.isoformat(),
            extra={"location": m.location, "organizer_id": m.organizer_id, "attendees": m.attendees},
        ))

    # ── Tareas ────────────────────────────────────────────────────────────────
    task_query = select(Task).order_by(Task.due_date.asc().nullslast())
    if not is_admin:
        task_query = task_query.where(
            or_(Task.assigned_to == user_id, Task.created_by == user_id)
        )
    task_result = await db.execute(task_query)
    for t in task_result.scalars().all():
        events.append(CalendarEvent(
            id=t.id,
            type="task",
            title=t.title,
            start=t.due_date.isoformat() if t.due_date else t.created_at.date().isoformat(),
            status=t.status,
            priority=t.priority,
            extra={"assigned_to": t.assigned_to, "description": t.description},
        ))

    # ── Filtrar por mes si se proporcionó ─────────────────────────────────────
    if month:
        events = [e for e in events if e.start.startswith(month)]

    return events


@router.get("/accrual/{user_id}")
async def get_accrual(
    user_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.models.user import User
    from app.services.accrual_service import calculate_accrual

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.hire_date:
        raise HTTPException(status_code=400, detail="User has no hire_date")

    result = calculate_accrual(user.hire_date.date() if hasattr(user.hire_date, 'date') else user.hire_date, user.country or "ES")
    result["user_id"] = user_id
    result["user_name"] = user.full_name
    return result


@router.get("/vacations/{user_id}.ics")
async def export_vacation_ics(
    user_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(get_current_user),
):
    from fastapi.responses import PlainTextResponse
    from app.services.ics_export import generate_ics, format_ics_date

    result = await db.execute(
        select(VacationRequest).where(
            VacationRequest.user_id == user_id,
            VacationRequest.status == "approved",
        ).order_by(VacationRequest.start_date.asc()).limit(50)
    )
    vacations = result.scalars().all()

    events = []
    for v in vacations:
        events.append({
            "start": v.start_date,
            "end": v.end_date or v.start_date,
            "summary": f"Vacation - {v.days_requested or 1} day(s)",
            "description": f"Vacation request approved on {v.decision_at.isoformat() if hasattr(v, 'decision_at') and v.decision_at else v.created_at.isoformat()}",
            "uid": f"vacation-{v.id}@successcore",
        })

    ics = generate_ics(events)
    return PlainTextResponse(ics, media_type="text/calendar",
                             headers={"Content-Disposition": f"attachment; filename=vacation_{user_id}.ics"})
