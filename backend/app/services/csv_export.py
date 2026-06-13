import io
import csv
import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger("successcore.csv_export")


async def export_all_employees_csv(db: AsyncSession) -> str:
    from app.models.user import User

    result = await db.execute(select(User).order_by(User.full_name.asc()))
    users = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        "id", "email", "full_name", "department", "role", "is_active",
        "base_salary", "hire_date", "contract_type", "country",
        "vacation_allowance", "locale", "timezone", "manager_id",
    ]
    writer.writerow(headers)

    for u in users:
        writer.writerow([
            u.id, u.email, u.full_name, u.department, u.role,
            "true" if u.is_active else "false", u.base_salary,
            u.hire_date.isoformat() if u.hire_date else "", u.contract_type,
            u.country, u.vacation_allowance, u.locale, u.timezone,
            u.manager_id or "",
        ])

    return output.getvalue()
