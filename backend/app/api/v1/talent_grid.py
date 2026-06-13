from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from app.api.dependencies import get_tenant_db, get_current_user, require_roles
from app.models.user import User
from app.models.grow import PerformanceReview, Objective

router = APIRouter()


def _get_user_id(user_payload: dict) -> str:
    sub = user_payload.get("sub", "")
    if "|" in sub:
        return sub.split("|")[-1]
    return sub or "unknown"


class EmployeeGridPosition(BaseModel):
    user_id: str
    full_name: str
    email: str
    department: Optional[str] = None
    role: str
    manager_name: Optional[str] = None
    hire_date: Optional[str] = None
    performance_score: float
    potential_score: float
    grid_x: int = 0
    grid_y: int = 0
    last_review_date: Optional[str] = None
    okr_progress: float = 0.0
    base_salary: Optional[float] = None


class SuccessionCandidate(BaseModel):
    user_id: str
    full_name: str
    role: str
    readiness_level: str
    target_roles: list


class TalentGridResponse(BaseModel):
    employees: list
    stats: dict
    succession_risks: list


@router.get("/talent-grid", response_model=TalentGridResponse)
async def get_talent_grid(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "manager", "super_admin"]))
):
    result = await db.execute(
        select(User).where(User.is_active == True).order_by(User.department)
    )
    users = result.scalars().all()

    user_ids = [u.id for u in users]
    manager_ids = [u.manager_id for u in users if u.manager_id]
    managers_result = await db.execute(select(User).where(User.id.in_(manager_ids)))
    managers = {m.id: m.full_name for m in managers_result.scalars().all()}

    reviews_result = await db.execute(
        select(PerformanceReview).where(PerformanceReview.employee_id.in_(user_ids))
    )
    reviews = reviews_result.scalars().all()
    latest_review_map = {}
    for r in reviews:
        if r.employee_id not in latest_review_map or (
            r.created_at and latest_review_map[r.employee_id].get("date")
            and r.created_at > latest_review_map[r.employee_id]["date"]
        ):
            score = 3.0
            if r.manager_evaluation and isinstance(r.manager_evaluation, dict):
                score = float(r.manager_evaluation.get("overall_score", 3))
            elif r.self_evaluation and isinstance(r.self_evaluation, dict):
                score = float(r.self_evaluation.get("overall_score", 3))
            latest_review_map[r.employee_id] = {"date": r.created_at, "score": score}

    okrs_result = await db.execute(
        select(func.avg(Objective.progress), Objective.owner_id).where(
            Objective.owner_id.in_(user_ids)
        ).group_by(Objective.owner_id)
    )
    okr_progress_map = {row[1]: round(row[0] or 0, 1) for row in okrs_result.all()}

    employees = []
    for u in users:
        rev_data = latest_review_map.get(u.id, {})
        perf_score = rev_data.get("score", 3.0)
        okr_prog = okr_progress_map.get(u.id, 0)
        potential_score = (perf_score * 0.4 + okr_prog * 0.3 + min(u.base_salary / 50000 * 5, 5) * 0.3) if u.base_salary else (perf_score * 0.6 + okr_prog * 0.4)
        potential_score = round(min(max(potential_score, 1), 5), 1)
        grid_x = 1 if perf_score < 2.5 else (2 if perf_score < 3.5 else 3)
        grid_y = 1 if potential_score < 2.5 else (2 if potential_score < 3.5 else 3)

        employees.append(EmployeeGridPosition(
            user_id=u.id,
            full_name=u.full_name or u.email,
            email=u.email,
            department=u.department,
            role=u.role,
            manager_name=managers.get(u.manager_id) if u.manager_id else None,
            hire_date=u.hire_date.isoformat() if u.hire_date else None,
            performance_score=round(perf_score, 1),
            potential_score=potential_score,
            grid_x=grid_x,
            grid_y=grid_y,
            last_review_date=rev_data.get("date").isoformat() if rev_data.get("date") else None,
            okr_progress=okr_prog,
            base_salary=u.base_salary,
        ))

    stats = {
        "total_employees": len(users),
        "high_performers": sum(1 for e in employees if e.performance_score >= 4),
        "high_potential": sum(1 for e in employees if e.potential_score >= 4),
        "needs_attention": sum(1 for e in employees if e.performance_score < 2.5),
        "stars": sum(1 for e in employees if e.performance_score >= 4 and e.potential_score >= 4),
        "rising_stars": sum(1 for e in employees if e.performance_score >= 3.5 and e.potential_score >= 4 and e.performance_score < 4),
        "core_players": sum(1 for e in employees if 2.5 <= e.performance_score < 4 and 2.5 <= e.potential_score < 4),
        "underperformers": sum(1 for e in employees if e.performance_score < 2.5 and e.potential_score < 3),
    }

    stars = [e for e in employees if e.performance_score >= 4 and e.potential_score >= 4]
    succession_risks = []
    critical_roles = ["manager", "hr_admin", "it_manager", "finance_manager"]
    for u in users:
        if u.role in critical_roles:
            successors = [e for e in stars if e.department == u.department and e.user_id != u.id]
            if len(successors) < 2:
                succession_risks.append({
                    "user_id": u.id,
                    "full_name": u.full_name or u.email,
                    "role": u.role,
                    "risk": "Sin sucesores preparados",
                    "potential_successors": [s.model_dump() for s in successors[:3]],
                })

    return TalentGridResponse(
        employees=[e.model_dump() for e in employees],
        stats=stats,
        succession_risks=succession_risks,
    )
