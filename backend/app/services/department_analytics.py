import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from collections import defaultdict

logger = logging.getLogger("successcore.dept_analytics")


async def get_department_analytics(db: AsyncSession) -> dict:
    from app.models.user import User
    from app.models.kudos import Kudos
    from app.models.training import CourseEnrollment
    from app.models.hire import Candidate, JobPosting

    users_res = await db.execute(select(User).where(User.is_active == True))
    users = users_res.scalars().all()

    dept_headcount: Dict[str, int] = defaultdict(int)
    dept_salaries: Dict[str, list] = defaultdict(list)
    for u in users:
        dept = u.department or "Unknown"
        dept_headcount[dept] += 1
        if u.base_salary > 0:
            dept_salaries[dept].append(u.base_salary)

    departments = []
    for dept, count in sorted(dept_headcount.items(), key=lambda x: x[1], reverse=True):
        salaries = dept_salaries.get(dept, [])
        avg_salary = round(sum(salaries) / len(salaries), 2) if salaries else 0
        departments.append({
            "department": dept,
            "headcount": count,
            "avg_salary": avg_salary,
            "pct_of_total": round(count / max(len(users), 1) * 100, 1),
        })

    cross_dept_kudos: Dict[tuple, int] = defaultdict(int)
    try:
        kudos_res = await db.execute(select(Kudos))
        for k in kudos_res.scalars().all():
            sender = next((u for u in users if u.id == k.sender_id), None)
            receiver = next((u for u in users if u.id == k.receiver_id), None)
            if sender and receiver and sender.department != receiver.department:
                key = (sender.department or "Unknown", receiver.department or "Unknown")
                cross_dept_kudos[key] += 1
    except Exception:
        pass

    collaboration = [
        {"from_dept": a, "to_dept": b, "kudos_count": c}
        for (a, b), c in sorted(cross_dept_kudos.items(), key=lambda x: x[1], reverse=True)[:20]
    ]

    return {
        "total_employees": len(users),
        "department_count": len(departments),
        "departments": departments,
        "cross_department_collaboration": collaboration,
    }
