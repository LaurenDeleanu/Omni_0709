from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.api.dependencies import get_tenant_db, get_current_user, require_roles

router = APIRouter()


class ClockInRequest(BaseModel):
    notes: str = ""
    project_id: str = ""
    task_id: str = ""


class ClockOutRequest(BaseModel):
    notes: str = ""


@router.post("/in", response_model=dict)
async def clock_in_endpoint(
    body: ClockInRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"])),
):
    from app.services.time_tracking_service import clock_in
    user_id = current_user.get("sub", "").split("|")[-1]
    try:
        return await clock_in(db, user_id, body.notes, body.project_id, body.task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/out", response_model=dict)
async def clock_out_endpoint(
    body: ClockOutRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"])),
):
    from app.services.time_tracking_service import clock_out
    user_id = current_user.get("sub", "").split("|")[-1]
    try:
        return await clock_out(db, user_id, body.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/active", response_model=dict)
async def get_active_session_endpoint(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.time_tracking_service import get_active_session
    user_id = current_user.get("sub", "").split("|")[-1]
    session = await get_active_session(db, user_id)
    return {"active": session is not None, "session": session}


@router.get("/logs", response_model=dict)
async def get_time_logs_endpoint(
    start_date: str = "",
    end_date: str = "",
    limit: int = 50,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.time_tracking_service import get_time_logs
    user_id = current_user.get("sub", "").split("|")[-1]
    logs = await get_time_logs(db, user_id, start_date if start_date else None, end_date if end_date else None, limit)
    return {"logs": logs, "count": len(logs)}


@router.get("/summary", response_model=dict)
async def get_timesheet_summary_endpoint(
    start_date: str = "",
    end_date: str = "",
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.time_tracking_service import get_timesheet_summary
    user_id = current_user.get("sub", "").split("|")[-1]
    return await get_timesheet_summary(db, user_id, start_date, end_date)
