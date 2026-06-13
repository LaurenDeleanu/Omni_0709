import logging
import zipfile
import io
import json
import csv
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger("successcore.gdpr_export")


async def build_gdpr_export_package(db: AsyncSession, user_id: str) -> bytes:
    from app.models.user import User
    from app.models.pay import Payslip
    from app.models.employee_history import EmployeeHistory
    from app.models.finance import ExpenseClaim, TimeLog
    from app.models.training import CourseEnrollment
    from app.models.kudos import Kudos
    from app.models.vacation import VacationRequest
    from app.models.comment import Comment

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")

    sections = {}

    sections["profile.json"] = json.dumps({
        "id": user.id, "email": user.email, "full_name": user.full_name,
        "department": user.department, "role": user.role,
        "hire_date": user.hire_date.isoformat() if user.hire_date else None,
        "contract_type": user.contract_type, "country": user.country,
        "vacation_allowance": user.vacation_allowance,
    }, ensure_ascii=False, indent=2)

    payslip_res = await db.execute(
        select(Payslip).where(Payslip.employee_id == user_id).order_by(Payslip.created_at.desc()).limit(24)
    )
    payslips = payslip_res.scalars().all()
    ps_csv = ["cycle_id,gross,net,deductions,status,created_at"]
    for p in payslips:
        ps_csv.append(f"{p.cycle_id},{p.gross_salary},{p.net_salary},{p.deductions},{p.status},{p.created_at}")
    sections["payslips.csv"] = "\n".join(ps_csv)

    hist_res = await db.execute(
        select(EmployeeHistory).where(EmployeeHistory.user_id == user_id).order_by(EmployeeHistory.start_date.desc())
    )
    history = hist_res.scalars().all()
    hist_csv = ["start_date,end_date,position,department,salary,reason"]
    for h in history:
        hist_csv.append(f"{h.start_date},{h.end_date or ''},{h.position or ''},{h.department or ''},{h.salary or ''},{h.reason or ''}")
    sections["employment_history.csv"] = "\n".join(hist_csv)

    expense_res = await db.execute(
        select(ExpenseClaim).where(ExpenseClaim.user_id == user_id).order_by(ExpenseClaim.created_at.desc()).limit(100)
    )
    expenses = expense_res.scalars().all()
    exp_csv = ["id,category,total_amount,status,description,created_at"]
    for e in expenses:
        exp_csv.append(f"{e.id},{e.category},{e.total_amount},{e.status},{e.description},{e.created_at}")
    sections["expenses.csv"] = "\n".join(exp_csv)

    kudos_res = await db.execute(
        select(Kudos).where(Kudos.receiver_id == user_id).order_by(Kudos.created_at.desc()).limit(50)
    )
    kudos_list = kudos_res.scalars().all()
    k_csv = ["id,sender_name,badge,message,created_at"]
    for k in kudos_list:
        k_csv.append(f"{k.id},{k.sender_name},{k.badge},{k.message},{k.created_at}")
    sections["kudos_received.csv"] = "\n".join(k_csv)

    try:
        course_res = await db.execute(
            select(CourseEnrollment).where(CourseEnrollment.user_id == user_id).order_by(CourseEnrollment.enrolled_at.desc()).limit(50)
        )
        courses = course_res.scalars().all()
        c_csv = ["id,course_id,status,enrolled_at,completed_at"]
        for c in courses:
            c_csv.append(f"{c.id},{c.course_id},{c.status},{c.enrolled_at},{c.completed_at}")
        sections["training.csv"] = "\n".join(c_csv)
    except Exception:
        pass

    try:
        vac_res = await db.execute(
            select(VacationRequest).where(VacationRequest.user_id == user_id).order_by(VacationRequest.start_date.desc()).limit(50)
        )
        vacs = vac_res.scalars().all()
        v_csv = ["id,start_date,end_date,days_requested,status"]
        for v in vacs:
            v_csv.append(f"{v.id},{v.start_date},{v.end_date},{v.days_requested},{v.status}")
        sections["vacation_requests.csv"] = "\n".join(v_csv)
    except Exception:
        pass

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in sections.items():
            zf.writestr(f"gdpr_export_{user.email}/{filename}", content)
    buf.seek(0)
    return buf.read()
