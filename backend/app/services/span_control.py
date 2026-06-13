import logging
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User

logger = logging.getLogger("successcore.span")


async def get_span_of_control(db: AsyncSession) -> dict:
    result = await db.execute(
        select(User).where(User.is_active == True)
    )
    users = result.scalars().all()

    direct_reports: Dict[str, List[dict]] = {}
    for u in users:
        if u.manager_id:
            if u.manager_id not in direct_reports:
                direct_reports[u.manager_id] = []
            direct_reports[u.manager_id].append({
                "id": u.id,
                "name": u.full_name or u.email,
                "department": u.department,
                "role": u.role,
            })

    manager_span: list = []
    too_wide: list = []
    too_narrow: list = []
    orphans: list = []

    manager_ids = set(direct_reports.keys())
    for mid in manager_ids:
        reports = direct_reports[mid]
        count = len(reports)
        entry = {"manager_id": mid, "direct_reports_count": count, "direct_reports": reports[:10]}
        manager_span.append(entry)
        if count > 12:
            too_wide.append(entry)
        elif count < 3 and count > 0:
            too_narrow.append(entry)

    for u in users:
        if u.id not in manager_ids and u.manager_id is None:
            name = u.full_name or u.email
            if "admin" not in name.lower() and "super" not in name.lower():
                orphans.append({"id": u.id, "name": name, "department": u.department, "role": u.role})

    return {
        "total_employees": len(users),
        "total_managers_with_reports": len(manager_span),
        "too_wide": too_wide,
        "too_narrow": too_narrow,
        "orphans": orphans,
        "all_spans": manager_span,
    }
