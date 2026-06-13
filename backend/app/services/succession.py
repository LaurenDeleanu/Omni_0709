import logging
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

logger = logging.getLogger("successcore.succession")

READINESS_LEVELS = {"ready_now": "Ready Now", "1_2_years": "1-2 Years", "3_5_years": "3-5 Years"}

_succession_plans: Dict[str, list] = {}


async def mark_critical_role(role_name: str, department: str, reason: str = "") -> dict:
    _succession_plans[role_name] = _succession_plans.get(role_name, []) or []
    return {"role": role_name, "department": department, "is_critical": True, "reason": reason}


async def add_successor(role_name: str, user_id: str, user_name: str, readiness: str, notes: str = "") -> dict:
    if readiness not in READINESS_LEVELS:
        raise ValueError(f"Invalid readiness: {readiness}")
    if role_name not in _succession_plans:
        _succession_plans[role_name] = []
    entry = {
        "user_id": user_id,
        "user_name": user_name,
        "readiness": readiness,
        "readiness_label": READINESS_LEVELS[readiness],
        "notes": notes,
        "added_at": datetime.now(timezone.utc).isoformat(),
    }
    _succession_plans[role_name].append(entry)
    return entry


async def get_succession_pipeline(db: AsyncSession) -> dict:
    critical_roles: List[dict] = []
    for role_name, successors in _succession_plans.items():
        ready_now = [s for s in successors if s["readiness"] == "ready_now"]
        key_risk = len(ready_now) == 0
        critical_roles.append({
            "role": role_name,
            "successors": successors,
            "ready_now_count": len(ready_now),
            "total_successors": len(successors),
            "key_person_risk": key_risk,
            "risk_level": "critical" if key_risk else "low" if len(successors) >= 2 else "medium",
        })

    from app.models.user import User
    users_res = await db.execute(select(User).where(User.is_active == True))
    users = users_res.scalars().all()

    potential_pool = []
    for u in users:
        score = 0
        dept = u.department or ""
        role = u.role or ""
        if "senior" in role.lower() or "lead" in role.lower():
            score += 2
        if "manager" in role.lower():
            score += 1
        if score > 0:
            potential_pool.append({
                "user_id": u.id,
                "name": u.full_name or u.email,
                "department": dept,
                "role": role,
                "potential_score": score,
            })

    return {
        "critical_roles_count": len(critical_roles),
        "total_successors": sum(c["total_successors"] for c in critical_roles),
        "critical_roles": critical_roles,
        "at_risk_roles": [c for c in critical_roles if c["risk_level"] == "critical"],
        "potential_successor_pool": potential_pool[:50],
    }
