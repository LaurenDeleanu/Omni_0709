"""
self_service.py — Employee self-service portal endpoints.
Profile management, time-off requests, payslip access, personal info updates.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from app.api.dependencies import get_tenant_db, get_current_user
from app.models.user import User
from app.models.calendar import VacationRequest

router = APIRouter(prefix="/self-service", tags=["Employee Self-Service"])


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    bank_iban: Optional[str] = None
    tax_id: Optional[str] = None


class TimeOffRequest(BaseModel):
    start_date: str
    end_date: str
    type: str = "vacation"
    reason: str = ""


@router.get("/profile")
async def get_my_profile(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Get current employee's full profile."""
    user_id = current_user.get("sub", "")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone or "",
        "address": user.address or "",
        "emergency_contact": user.emergency_contact or "",
        "emergency_phone": user.emergency_phone or "",
        "bank_iban": user.iban or "",
        "tax_id": user.social_security_number or "",
        "role": user.role or "employee",
        "department": getattr(user, "department", ""),
        "manager": getattr(user, "manager", ""),
        "hire_date": user.hire_date.isoformat() if user.hire_date else None,
    }


@router.put("/profile")
async def update_my_profile(
    body: ProfileUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Update current employee's personal information."""
    user_id = current_user.get("sub", "")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.phone is not None:
        user.phone = body.phone
    if body.address is not None:
        user.address = body.address
    if body.emergency_contact is not None:
        user.emergency_contact = body.emergency_contact
    if body.emergency_phone is not None:
        user.emergency_phone = body.emergency_phone
    if body.bank_iban is not None:
        user.iban = body.bank_iban
    if body.tax_id is not None:
        user.social_security_number = body.tax_id

    user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"status": "updated", "message": "Profile updated successfully"}


@router.get("/time-off")
async def get_my_time_off(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Get current employee's vacation/time-off requests."""
    user_id = current_user.get("sub", "")
    result = await db.execute(
        select(VacationRequest)
        .where(VacationRequest.user_id == user_id)
        .order_by(VacationRequest.created_at.desc())
        .limit(50)
    )
    requests = result.scalars().all()

    return {
        "requests": [
            {
                "id": r.id,
                "start_date": r.start_date.isoformat() if r.start_date else None,
                "end_date": r.end_date.isoformat() if r.end_date else None,
                "type": getattr(r, "type", "vacation"),
                "status": getattr(r, "status", "pending"),
                "reason": getattr(r, "reason", ""),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in requests
        ],
        "remaining_days": 22,  # Default annual allowance
    }


@router.post("/time-off")
async def request_time_off(
    body: TimeOffRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Submit a new time-off request."""
    user_id = current_user.get("sub", "")
    import uuid

    request = VacationRequest(
        id=uuid.uuid4().hex,
        user_id=user_id,
        start_date=datetime.fromisoformat(body.start_date),
        end_date=datetime.fromisoformat(body.end_date),
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    # Set optional fields if they exist on the model
    if hasattr(VacationRequest, "reason"):
        request.reason = body.reason
    if hasattr(VacationRequest, "type"):
        request.type = body.type

    db.add(request)
    await db.commit()

    return {"status": "submitted", "request_id": request.id, "message": "Time-off request submitted"}


@router.get("/payslips")
async def get_my_payslips(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Get current employee's payslips."""
    user_id = current_user.get("sub", "")
    from app.models.pay import Payslip
    result = await db.execute(
        select(Payslip)
        .where(Payslip.employee_id == user_id)
        .order_by(Payslip.period_start.desc())
        .limit(24)
    )
    payslips = result.scalars().all()

    return {
        "payslips": [
            {
                "id": p.id,
                "period_start": p.period_start.isoformat() if p.period_start else None,
                "period_end": p.period_end.isoformat() if p.period_end else None,
                "gross_salary": p.gross_salary,
                "net_salary": p.net_salary,
                "status": getattr(p, "status", "paid"),
            }
            for p in payslips
        ]
    }
