import logging
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger("successcore.profiles")


async def get_employee_social_profile(db: AsyncSession, user_id: str) -> dict:
    from app.models.user import User
    from app.models.kudos import Kudos
    from app.models.training import CourseEnrollment
    from app.models.work import Project
    from datetime import datetime, timezone

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")

    manager_name = None
    if user.manager_id:
        mgr_res = await db.execute(select(User).where(User.id == user.manager_id))
        mgr = mgr_res.scalar_one_or_none()
        if mgr:
            manager_name = mgr.full_name or mgr.email

    kudos_received = 0
    kudos_given = 0
    try:
        received_res = await db.execute(select(Kudos).where(Kudos.receiver_id == user_id))
        kudos_received = len(received_res.scalars().all())
        given_res = await db.execute(select(Kudos).where(Kudos.sender_id == user_id))
        kudos_given = len(given_res.scalars().all())
    except Exception:
        pass

    courses_completed = 0
    try:
        crs_res = await db.execute(
            select(CourseEnrollment).where(CourseEnrollment.user_id == user_id, CourseEnrollment.status == "completed")
        )
        courses_completed = len(crs_res.scalars().all())
    except Exception:
        pass

    skills = _extract_skills(user)

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "department": user.department,
        "role": user.role,
        "hire_date": user.hire_date.isoformat() if user.hire_date else None,
        "contract_type": user.contract_type,
        "manager_name": manager_name,
        "country": user.country,
        "locale": user.locale,
        "kudos_received": kudos_received,
        "kudos_given": kudos_given,
        "courses_completed": courses_completed,
        "skills": skills,
        "is_active": user.is_active,
    }


def _extract_skills(user) -> List[str]:
    from app.services.skills_matrix import SKILL_KEYWORDS
    text = f"{user.full_name or ''} {user.department or ''} {user.role or ''}".lower()
    found = []
    for category, keywords in SKILL_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            found.append(category)
    return found
