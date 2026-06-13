from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_tenant_db, require_roles
from app.services.onboarding_planner import (
    generate_onboarding_plan,
    assign_onboarding_buddy,
    complete_onboarding,
    get_onboarding_progress,
    generate_welcome_message,
)
from pydantic import BaseModel

router = APIRouter()


class StartOnboardingRequest(BaseModel):
    employee_id: str | None = None
    user_id: str | None = None


@router.post("/{employee_id}/generate-plan", dependencies=[Depends(require_roles(["hr_admin", "super_admin", "manager"]))])
async def api_generate_onboarding_plan(employee_id: str, db: AsyncSession = Depends(get_tenant_db)):
    try:
        plan = await generate_onboarding_plan(employee_id, db)
        return plan
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{employee_id}/start", dependencies=[Depends(require_roles(["hr_admin", "super_admin"]))])
async def api_start_onboarding(employee_id: str, db: AsyncSession = Depends(get_tenant_db)):
    try:
        result = await complete_onboarding(employee_id, user_id=employee_id, db=db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{employee_id}/progress", dependencies=[Depends(require_roles(["hr_admin", "super_admin", "manager"]))])
async def api_get_onboarding_progress(employee_id: str, db: AsyncSession = Depends(get_tenant_db)):
    try:
        progress = await get_onboarding_progress(employee_id, db)
        return progress
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{employee_id}/assign-buddy", dependencies=[Depends(require_roles(["hr_admin", "super_admin"]))])
async def api_assign_onboarding_buddy(employee_id: str, db: AsyncSession = Depends(get_tenant_db)):
    try:
        result = await assign_onboarding_buddy(employee_id, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{employee_id}/welcome-message", dependencies=[Depends(require_roles(["hr_admin", "super_admin", "manager"]))])
async def api_get_welcome_message(employee_id: str, db: AsyncSession = Depends(get_tenant_db)):
    try:
        message = await generate_welcome_message(employee_id, db)
        return message
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
