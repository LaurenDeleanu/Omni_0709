import logging
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from collections import defaultdict

logger = logging.getLogger("successcore.recommendations")


async def recommend_courses(db: AsyncSession, user_id: str) -> dict:
    from app.models.user import User
    from app.models.training import Course, CourseEnrollment

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")

    enrolled_res = await db.execute(
        select(CourseEnrollment).where(CourseEnrollment.user_id == user_id)
    )
    enrolled = enrolled_res.scalars().all()
    enrolled_course_ids = {e.course_id for e in enrolled}

    all_courses_res = await db.execute(select(Course))
    all_courses = all_courses_res.scalars().all()

    available = [c for c in all_courses if c.id not in enrolled_course_ids]

    scored: List[dict] = []
    for course in available:
        score = 0
        if course.department and user.department and course.department.lower() == user.department.lower():
            score += 3
        if course.level and user.role:
            if course.level.lower() in user.role.lower():
                score += 2
        if course.skills and user.role:
            for skill in (course.skills or "").split(","):
                if skill.strip().lower() in (user.role or "").lower():
                    score += 1

        scored.append({
            "course_id": course.id,
            "title": course.title,
            "department": course.department,
            "level": course.level,
            "score": score,
            "reason": _build_reason(score, course, user),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    top = scored[:5]
    category_groups = defaultdict(list)
    for item in scored:
        dept = item.get("department", "General")
        category_groups[dept].append(item)

    return {
        "user_id": user_id,
        "user_name": user.full_name,
        "department": user.department,
        "completed_courses": len(enrolled_course_ids),
        "recommendations": top,
        "by_department": {k: v[:3] for k, v in category_groups.items()},
    }


def _build_reason(score: int, course, user) -> str:
    if score >= 3:
        return f"Aligned with your department ({user.department})"
    elif score >= 2:
        return f"Fits your role ({user.role})"
    elif score >= 1:
        return "Skill match based on your profile"
    return "Recommended for your development"
