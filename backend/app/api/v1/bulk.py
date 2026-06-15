from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List
from pydantic import BaseModel

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.dependencies import get_tenant_db, require_roles
from app.models.finance import ExpenseClaim
from app.models.pay import PayrollCycle, Payslip
from app.models.training import CourseEnrollment

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


class BulkIdsIn(BaseModel):
    ids: List[str]


@limiter.limit("10/minute")
@router.post("/expenses/approve")
async def bulk_approve_expenses(
    request: Request,
    body: BulkIdsIn,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    if not body.ids:
        raise HTTPException(status_code=400, detail="No ids provided")

    result = await db.execute(
        update(ExpenseClaim).where(ExpenseClaim.id.in_(body.ids)).values(status="approved")
    )
    await db.commit()
    return {"approved": result.rowcount, "ids": body.ids}


@limiter.limit("10/minute")
@router.post("/payslips/generate")
async def bulk_generate_payslips(
    request: Request,
    cycle_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    cycle_res = await db.execute(select(PayrollCycle).where(PayrollCycle.id == cycle_id))
    cycle = cycle_res.scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")

    from app.models.user import User
    users_res = await db.execute(select(User).where(User.is_active == True))
    users = users_res.scalars().all()

    created = 0
    for user in users:
        existing = await db.execute(
            select(Payslip).where(Payslip.cycle_id == cycle_id, Payslip.employee_id == user.id)
        )
        if existing.scalar_one_or_none():
            continue
        import uuid
        payslip = Payslip(
            id=uuid.uuid4().hex,
            cycle_id=cycle_id,
            employee_id=user.id,
            gross_salary=0.0,
            net_salary=0.0,
            status="draft"
        )
        db.add(payslip)
        created += 1

    await db.commit()
    return {"cycle_id": cycle_id, "payslips_created": created, "total_users": len(users)}


@limiter.limit("10/minute")
@router.post("/courses/assign")
async def bulk_assign_courses(
    request: Request,
    course_id: str,
    body: BulkIdsIn,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    if not body.ids:
        raise HTTPException(status_code=400, detail="No user ids provided")

    course_res = await db.execute(select(Course).where(Course.id == course_id))
    from app.models.training import Course
    course = course_res.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    assigned = 0
    import uuid
    from datetime import datetime, timezone
    for user_id in body.ids:
        existing = await db.execute(
            select(CourseEnrollment).where(CourseEnrollment.course_id == course_id, CourseEnrollment.user_id == user_id)
        )
        if existing.scalar_one_or_none():
            continue
        enrollment = CourseEnrollment(
            id=uuid.uuid4().hex,
            course_id=course_id,
            user_id=user_id,
            status="enrolled",
            enrolled_at=datetime.now(timezone.utc)
        )
        db.add(enrollment)
        assigned += 1

    await db.commit()
    return {"course_id": course_id, "title": course.title, "assigned": assigned}
