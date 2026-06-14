"""
performance_calibration.py — Calibration meetings, forced distribution, promotion tracking.
Uses existing manager_evaluation JSON field on PerformanceReview for rating data.
"""
import logging
import statistics
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger("successcore.calibration")

FORCED_DISTRIBUTION = {
    "top": 0.15, "strong": 0.30, "solid": 0.40, "low": 0.10, "bottom": 0.05,
}


def _extract_rating(evaluation_json: dict) -> float:
    """Extract overall rating from evaluation JSON. Default 3.0 if not present."""
    if not evaluation_json:
        return 3.0
    return float(evaluation_json.get("overall_rating", evaluation_json.get("rating", 3.0)))


def _extract_potential(evaluation_json: dict) -> int:
    """Extract potential rating (1-5) from evaluation JSON."""
    if not evaluation_json:
        return 3
    return int(evaluation_json.get("potential", evaluation_json.get("potential_rating", 3)))


async def analyze_team_performance(
    db: AsyncSession,
    tenant_id: str,
    manager_id: Optional[str] = None,
) -> dict:
    from app.models.grow import PerformanceReview
    from app.models.user import User

    query = select(PerformanceReview, User).join(User, PerformanceReview.employee_id == User.id)
    if manager_id:
        query = query.where(User.manager_id == manager_id)

    result = await db.execute(query)
    rows = result.all()

    if not rows:
        return {"employees": [], "calibration": {}, "summary": {}}

    scores = []
    employees = []
    for review, user in rows:
        score = _extract_rating(review.manager_evaluation)
        scores.append(score)
        potential = _extract_potential(review.manager_evaluation)
        employees.append({
            "id": user.id,
            "name": user.full_name,
            "email": user.email,
            "department": getattr(user, "department", ""),
            "rating": score,
            "potential": potential,
            "review_id": review.id,
            "cycle": review.cycle_name,
            "status": review.status,
        })

    mean = statistics.mean(scores)
    stdev = statistics.stdev(scores) if len(scores) > 1 else 0
    sorted_employees = sorted(employees, key=lambda e: e["rating"], reverse=True)
    n = len(employees)

    distribution = {
        "top": sorted_employees[:max(1, int(n * FORCED_DISTRIBUTION["top"]))],
        "strong": sorted_employees[int(n * FORCED_DISTRIBUTION["top"]):int(n * (FORCED_DISTRIBUTION["top"] + FORCED_DISTRIBUTION["strong"]))],
        "solid": sorted_employees[int(n * (FORCED_DISTRIBUTION["top"] + FORCED_DISTRIBUTION["strong"])):int(n * (1 - FORCED_DISTRIBUTION["low"] - FORCED_DISTRIBUTION["bottom"]))],
        "low": sorted_employees[int(n * (1 - FORCED_DISTRIBUTION["low"] - FORCED_DISTRIBUTION["bottom"])):int(n * (1 - FORCED_DISTRIBUTION["bottom"]))],
        "bottom": sorted_employees[int(n * (1 - FORCED_DISTRIBUTION["bottom"])):],
    }

    promotions = [e for e in employees if e.get("potential", 3) >= 4 and e["rating"] >= 4]
    pip_candidates = distribution.get("bottom", []) + distribution.get("low", [])[:max(1, len(distribution.get("low", [])) // 2)]

    return {
        "employees": employees, "count": n,
        "mean_rating": round(mean, 2), "stdev": round(stdev, 2),
        "calibration": {tier: [{"id": e["id"], "name": e["name"], "rating": e["rating"]} for e in tier_employees] for tier, tier_employees in distribution.items()},
        "promotion_recommendations": promotions, "pip_candidates": pip_candidates,
        "distribution_pct": {tier: round(len(tier_employees) / n * 100, 1) if n > 0 else 0 for tier, tier_employees in distribution.items()},
    }


async def get_promotion_tracking(
    db: AsyncSession, tenant_id: str, manager_id: Optional[str] = None,
) -> list[dict]:
    from app.models.grow import PerformanceReview
    from app.models.user import User

    query = select(User).where(User.is_active == True)
    if manager_id:
        query = query.where(User.manager_id == manager_id)

    result = await db.execute(query)
    users = result.scalars().all()

    tracking = []
    for user in users:
        reviews_result = await db.execute(
            select(PerformanceReview)
            .where(PerformanceReview.employee_id == user.id)
            .order_by(PerformanceReview.created_at.desc())
            .limit(3)
        )
        reviews = reviews_result.scalars().all()

        avg_rating = statistics.mean([_extract_rating(r.manager_evaluation) for r in reviews]) if reviews else 0
        potential = max([_extract_potential(r.manager_evaluation) for r in reviews]) if reviews else 0
        readiness = min(round(avg_rating * 25, 1), 100) if avg_rating > 0 else 0

        tracking.append({
            "id": user.id, "name": user.full_name, "email": user.email,
            "avg_rating": round(avg_rating, 2), "potential": potential,
            "promotion_readiness": readiness,
            "recommendation": "ready" if readiness >= 80 else "developing" if readiness >= 60 else "not_ready",
        })

    return sorted(tracking, key=lambda t: t["promotion_readiness"], reverse=True)


async def calibrate_cycle(
    db: AsyncSession, tenant_id: str, cycle_id: Optional[str] = None,
) -> dict:
    from app.models.grow import PerformanceReview

    query = select(PerformanceReview)
    if cycle_id:
        query = query.where(PerformanceReview.cycle_name == cycle_id)

    result = await db.execute(query)
    reviews = result.scalars().all()

    if not reviews:
        return {"status": "no_data", "reviews": 0}

    by_manager: dict[str, list[float]] = {}
    for r in reviews:
        mgr = r.manager_id or "unknown"
        score = _extract_rating(r.manager_evaluation)
        by_manager.setdefault(mgr, []).append(score)

    manager_stats = {}
    for mgr, scores in by_manager.items():
        manager_stats[mgr] = {
            "count": len(scores),
            "mean": round(statistics.mean(scores), 2),
            "stdev": round(statistics.stdev(scores), 2) if len(scores) > 1 else 0,
        }

    all_scores = [_extract_rating(r.manager_evaluation) for r in reviews]
    global_mean = statistics.mean(all_scores)
    global_stdev = statistics.stdev(all_scores) if len(all_scores) > 1 else 1

    return {
        "status": "calibrated", "total_reviews": len(reviews),
        "global_mean": round(global_mean, 2), "global_stdev": round(global_stdev, 2),
        "managers": manager_stats,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
