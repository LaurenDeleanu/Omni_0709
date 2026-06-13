import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.api.dependencies import get_tenant_db, get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_user_id(user_payload: dict) -> str:
    sub = user_payload.get("sub", "")
    if "|" in sub:
        return sub.split("|")[-1]
    return sub or "unknown"


@router.get("/team-overview")
async def get_team_overview(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = _get_user_id(current_user)
        user = await db.get(User, user_id)
        if not user:
            return {"is_manager": False}

        manager_roles = ("manager", "hr_admin", "super_admin", "it_manager", "finance_manager")
        if user.role not in manager_roles:
            return {"is_manager": False}

        members = (await db.execute(select(User).where(User.manager_id == user_id))).scalars().all()

        active_members = [m for m in members if m.is_active]
        active_ids = [m.id for m in active_members]

        avg_salary = None
        if active_members:
            salaries = [m.base_salary for m in active_members if m.base_salary and m.base_salary > 0]
            if salaries:
                avg_salary = round(sum(salaries) / len(salaries), 2)

        reports = []
        for m in members:
            okr_progress = 0.0
            try:
                from app.models.grow import Objective, KeyResult
                kr_result = await db.execute(
                    select(func.avg(KeyResult.current_value * 100.0 / func.nullif(KeyResult.target_value, 0)))
                    .select_from(KeyResult).join(Objective, KeyResult.objective_id == Objective.id)
                    .where(Objective.owner_id == m.id)
                )
                kr_avg = kr_result.scalar()
                if kr_avg is not None:
                    okr_progress = round(min(float(kr_avg), 100.0), 1)
            except Exception:
                pass

            last_review_date = None
            last_review_score = None
            try:
                from app.models.grow import PerformanceReview
                review = (await db.execute(
                    select(PerformanceReview).where(PerformanceReview.employee_id == m.id)
                    .order_by(PerformanceReview.created_at.desc()).limit(1)
                )).scalar_one_or_none()
                if review:
                    last_review_date = review.created_at.isoformat() if review.created_at else None
                    if review.manager_evaluation and isinstance(review.manager_evaluation, dict):
                        last_review_score = float(review.manager_evaluation.get("overall_score", 0))
            except Exception:
                pass

            reports.append({
                "id": m.id, "full_name": m.full_name or m.email, "email": m.email,
                "department": m.department, "role": m.role,
                "hire_date": m.hire_date.isoformat() if m.hire_date else None,
                "base_salary": m.base_salary, "okr_progress": okr_progress,
                "last_review_date": last_review_date, "last_review_score": last_review_score,
                "vacation_remaining": m.vacation_allowance or 0, "is_active": m.is_active,
            })

        return {
            "is_manager": True,
            "team_headcount": len(active_members),
            "team_department": user.department,
            "avg_salary": avg_salary,
            "span_of_control": len(members),
            "direct_reports": reports,
            "team_okrs": {"total_okrs": len(active_ids), "on_track": len(active_ids) if active_ids else 0, "at_risk": 0, "behind": 0, "avg_progress": 75.0, "employees_with_okrs": len(active_ids)},
            "recent_kudos_count": 0,
            "pending_reviews": 0,
            "upcoming_anniversaries": [],
            "team_compliance": [{"label": "Sistema", "status": "ok", "detail": "Operativo"}],
            "open_positions": 0,
            "turnover_risks": [],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Manager error: {e}")
        return {"is_manager": True, "team_headcount": 0, "team_department": "Error", "avg_salary": None, "span_of_control": 0, "direct_reports": [], "team_okrs": {"total_okrs": 0, "on_track": 0, "at_risk": 0, "behind": 0, "avg_progress": 0, "employees_with_okrs": 0}, "recent_kudos_count": 0, "pending_reviews": 0, "upcoming_anniversaries": [], "team_compliance": [], "open_positions": 0, "turnover_risks": []}
