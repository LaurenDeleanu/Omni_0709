from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.dependencies import get_global_db, require_roles, get_current_user, check_module_enabled
from app.models.scheduled_report import ScheduledReport
from app.schemas.scheduled_report import ScheduleCreate, ScheduleResponse
from typing import List
from app.tasks.scheduled_reports import send_scheduled_report
import uuid

router = APIRouter(dependencies=[Depends(check_module_enabled("schedules"))])


@router.get("/", response_model=List[ScheduleResponse])
async def list_schedules(
    db: AsyncSession = Depends(get_global_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id", "acme_corp")
    result = await db.execute(
        select(ScheduledReport)
        .where(ScheduledReport.tenant_id == tenant_id)
        .order_by(ScheduledReport.created_at.desc())
    )
    return result.scalars().all()

@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_in: ScheduleCreate,
    db: AsyncSession = Depends(get_global_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id", "acme_corp")

    entry = ScheduledReport(
        id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        **schedule_in.model_dump()
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry

@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_global_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id", "acme_corp")

    result = await db.execute(
        select(ScheduledReport).where(
            ScheduledReport.id == schedule_id,
            ScheduledReport.tenant_id == tenant_id
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Programación no encontrada")

    await db.delete(entry)
    await db.commit()
    return None

@router.post("/{schedule_id}/trigger", status_code=status.HTTP_200_OK)
async def trigger_schedule_now(
    schedule_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_global_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id", "acme_corp")

    result = await db.execute(
        select(ScheduledReport).where(
            ScheduledReport.id == schedule_id,
            ScheduledReport.tenant_id == tenant_id
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Programación no encontrada")

    background_tasks.add_task(send_scheduled_report, entry.email_to, entry.tenant_id)
    return {"message": "Reporte encolado para su envío inmediato en background."}
