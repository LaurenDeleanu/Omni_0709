import logging
import io
import zipfile
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.pay import Payslip, PayrollCycle
from app.models.employee_history import EmployeeHistory

logger = logging.getLogger("successcore.export")


async def export_employee_data(db: AsyncSession, user_id: str) -> bytes:
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")

    history_res = await db.execute(
        select(EmployeeHistory).where(EmployeeHistory.user_id == user_id).order_by(EmployeeHistory.start_date.desc())
    )
    history = history_res.scalars().all()

    payslip_res = await db.execute(
        select(Payslip).where(Payslip.employee_id == user_id).order_by(Payslip.created_at.desc()).limit(24)
    )
    payslips = payslip_res.scalars().all()

    csv_data = [
        "Field,Value",
        f"email,{user.email}",
        f"full_name,{user.full_name}",
        f"department,{user.department}",
        f"role,{user.role}",
        f"hire_date,{user.hire_date}",
        f"contract_type,{user.contract_type}",
        f"phone_number,{user.phone_number}",
        f"vacation_allowance,{user.vacation_allowance}",
        f"is_active,{user.is_active}",
        "",
        "Employment History",
        "Start Date,End Date,Position,Department,Salary,Reason",
    ]
    for h in history:
        csv_data.append(f"{h.start_date},{h.end_date or ''},{h.position or ''},{h.department or ''},{h.salary or ''},{h.reason or ''}")

    csv_data.append("")
    csv_data.append("Payslips")
    csv_data.append("Cycle,Gross,Net,Tax,Status,Created")
    for p in payslips:
        csv_data.append(f"{p.cycle_id},{p.gross_salary},{p.net_salary},{p.tax_deducted or 0},{p.status},{p.created_at}")

    import json
    json_data = json.dumps({
        "email": user.email,
        "full_name": user.full_name,
        "department": user.department,
        "role": user.role,
        "hire_date": user.hire_date.isoformat() if user.hire_date else None,
        "employment_history": [
            {"start": h.start_date.isoformat() if h.start_date else None, "end": h.end_date.isoformat() if h.end_date else None, "position": h.position, "salary": h.salary}
            for h in history
        ],
        "payslip_count": len(payslips),
    }, ensure_ascii=False, default=str)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"export_{user.email}/profile.csv", "\n".join(csv_data))
        zf.writestr(f"export_{user.email}/profile.json", json_data)
    buf.seek(0)
    return buf.read()
