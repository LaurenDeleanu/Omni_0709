import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

logger = logging.getLogger("successcore.people_analytics")


def _months_ago(months: int) -> datetime:
    """Approximate date N months ago (30 days per month)."""
    return datetime.now(timezone.utc) - timedelta(days=30 * months)


def _month_start(offset_months: int = 0) -> datetime:
    """First day of month, offset_months ago from current month."""
    now = datetime.now(timezone.utc) - timedelta(days=30 * offset_months)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def _query_matview(db: AsyncSession, view_name: str) -> List[Any]:
    result = await db.execute(text(f"SELECT * FROM {view_name}"))
    return result.fetchall()


async def get_headcount_trends(db: AsyncSession, months: int = 12) -> Dict[str, Any]:
    from app.models.user import User

    labels = []
    data_active = []
    data_total = []

    for i in range(months - 1, -1, -1):
        month_start = _month_start(i)
        month_end = _month_start(i - 1) if i > 0 else datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        active_res = await db.execute(
            select(func.count(User.id)).where(
                User.is_active == True,
                User.created_at < month_end
            )
        )
        total_res = await db.execute(
            select(func.count(User.id)).where(User.created_at < month_end)
        )

        labels.append(month_start.strftime("%b %Y"))
        data_active.append(active_res.scalar() or 0)
        data_total.append(total_res.scalar() or 0)

    try:
        mat_rows = await _query_matview(db, "mv_employee_headcount")
        total_from_mv = sum(r.total_count for r in mat_rows)
    except Exception:
        total_from_mv = None

    return {
        "labels": labels,
        "active": data_active,
        "total": data_total,
        "matview_total": total_from_mv,
    }


async def get_turnover_analysis(db: AsyncSession, months: int = 12) -> Dict[str, Any]:
    from app.models.user import User
    from app.models.employee_history import EmployeeHistory

    since = _months_ago(months)

    end_date_rows = await db.execute(
        select(
            User.department,
            func.count(EmployeeHistory.id)
        )
        .select_from(EmployeeHistory)
        .join(User, EmployeeHistory.user_id == User.id)
        .where(
            EmployeeHistory.end_date >= since.date(),
            EmployeeHistory.end_date.isnot(None)
        )
        .group_by(User.department)
    )
    by_department = {row[0] or "Unassigned": row[1] for row in end_date_rows.fetchall()}

    tenure_rows = await db.execute(
        select(
            EmployeeHistory.user_id,
            EmployeeHistory.start_date,
            EmployeeHistory.end_date
        ).where(
            EmployeeHistory.end_date >= since.date(),
            EmployeeHistory.end_date.isnot(None)
        )
    )
    tenure_buckets = {"<1yr": 0, "1-3yr": 0, "3-5yr": 0, "5yr+": 0}
    for row in tenure_rows.fetchall():
        if row.start_date:
            tenure_days = (row.end_date - row.start_date).days if row.start_date else 0
            tenure_years = tenure_days / 365.0
            if tenure_years < 1:
                tenure_buckets["<1yr"] += 1
            elif tenure_years < 3:
                tenure_buckets["1-3yr"] += 1
            elif tenure_years < 5:
                tenure_buckets["3-5yr"] += 1
            else:
                tenure_buckets["5yr+"] += 1

    total_exits = sum(by_department.values())

    all_active_res = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_headcount = all_active_res.scalar() or 1

    return {
        "total_exits": total_exits,
        "turnover_rate_pct": round(total_exits / max(active_headcount, 1) * 100, 2),
        "by_department": by_department,
        "by_tenure": tenure_buckets,
        "period_months": months,
    }


async def get_diversity_metrics(db: AsyncSession) -> Dict[str, Any]:
    from app.models.user import User

    country_rows = await db.execute(
        select(
            User.department,
            User.country,
            func.count(User.id)
        )
        .where(User.is_active == True)
        .group_by(User.department, User.country)
        .order_by(User.department, func.count(User.id).desc())
    )
    by_country = {}
    for row in country_rows.fetchall():
        dept = row[0] or "Unassigned"
        country = row[1] or "Unknown"
        count = row[2]
        if dept not in by_country:
            by_country[dept] = {}
        by_country[dept][country] = count

    contract_rows = await db.execute(
        select(
            User.department,
            User.contract_type,
            func.count(User.id)
        )
        .where(User.is_active == True)
        .group_by(User.department, User.contract_type)
    )
    by_contract = {}
    for row in contract_rows.fetchall():
        dept = row[0] or "Unassigned"
        ct = row[1] or "Unknown"
        count = row[2]
        if dept not in by_contract:
            by_contract[dept] = {}
        by_contract[dept][ct] = count

    dept_counts_res = await db.execute(
        select(
            User.department,
            func.count(User.id)
        )
        .where(User.is_active == True)
        .group_by(User.department)
    )
    dept_totals = {row[0] or "Unassigned": row[1] for row in dept_counts_res.fetchall()}

    return {
        "by_country": by_country,
        "by_contract_type": by_contract,
        "department_totals": dept_totals,
    }


async def get_span_of_control(db: AsyncSession) -> Dict[str, Any]:
    from app.models.user import User

    manager_rows = await db.execute(
        select(
            User.manager_id,
            func.count(User.id)
        )
        .where(User.is_active == True, User.manager_id.isnot(None))
        .group_by(User.manager_id)
    )
    spans = {}
    for row in manager_rows.fetchall():
        spans[row[0]] = row[1]

    non_zero = [v for v in spans.values() if v > 0]
    avg_span = round(sum(non_zero) / len(non_zero), 1) if non_zero else 0

    manager_info = {}
    if spans:
        mgr_rows = await db.execute(
            select(User.id, User.full_name, User.department)
            .where(User.id.in_(list(spans.keys())))
        )
        for m in mgr_rows.fetchall():
            manager_info[m[0]] = {"name": m[1] or m[0], "department": m[2]}

    distribution = {}
    for v in spans.values():
        bucket = "1-3" if v <= 3 else "4-7" if v <= 7 else "8-15" if v <= 15 else "15+"
        distribution[bucket] = distribution.get(bucket, 0) + 1

    return {
        "average_span": avg_span,
        "max_span": max(spans.values()) if spans else 0,
        "min_span": min(spans.values()) if spans else 0,
        "distribution": distribution,
        "managers": {mid: {"span": count, **manager_info.get(mid, {"name": mid, "department": None})} for mid, count in spans.items()},
    }


async def get_time_to_hire(db: AsyncSession) -> Dict[str, Any]:
    from app.models.hire import Candidate, JobPosting

    rows = await db.execute(
        select(
            Candidate.job_id,
            JobPosting.title,
            JobPosting.created_at,
            Candidate.created_at
        )
        .select_from(Candidate)
        .join(JobPosting, Candidate.job_id == JobPosting.id)
        .where(Candidate.stage == "hired")
    )
    per_hire = []
    for row in rows.fetchall():
        if row[2] and row[3]:
            days = (row[3] - row[2]).days
            per_hire.append({
                "job_id": row[0],
                "job_title": row[1],
                "days_to_hire": days,
            })

    all_days = [h["days_to_hire"] for h in per_hire]
    avg_days = round(sum(all_days) / len(all_days), 1) if all_days else 0

    return {
        "average_days_to_hire": avg_days,
        "median_days_to_hire": round(sorted(all_days)[len(all_days) // 2], 1) if all_days else 0,
        "total_hires": len(per_hire),
        "per_job": per_hire,
    }


async def get_training_roi(db: AsyncSession) -> Dict[str, Any]:
    from app.models.training import CourseEnrollment, Course
    from app.models.grow import PerformanceReview

    try:
        mat_rows = await _query_matview(db, "mv_training_completion")
        mv_data = {}
        for r in mat_rows:
            mv_data[r.course_id] = {
                "total_enrollments": r.total_enrollments,
                "completed_count": r.completed_count,
                "completion_rate": float(r.completion_rate),
                "avg_score": float(r.avg_score),
                "avg_time_spent_seconds": int(r.avg_time_spent_seconds or 0),
            }
    except Exception:
        mv_data = {}

    perf_rows = await db.execute(select(PerformanceReview.employee_id, PerformanceReview.self_evaluation, PerformanceReview.manager_evaluation))
    user_perf = {}
    for row in perf_rows.fetchall():
        scores = []
        se = row[1] or {}
        me = row[2] or {}
        for val in se.values():
            if isinstance(val, (int, float)):
                scores.append(float(val))
        for val in me.values():
            if isinstance(val, (int, float)):
                scores.append(float(val))
        if scores:
            user_perf[row[0]] = sum(scores) / len(scores)

    enroll_rows = await db.execute(
        select(
            Course.id,
            Course.title,
            CourseEnrollment.user_id,
            CourseEnrollment.status,
            CourseEnrollment.score,
        )
        .select_from(CourseEnrollment)
        .join(Course, CourseEnrollment.course_id == Course.id)
    )
    course_roi = {}
    for row in enroll_rows.fetchall():
        cid = row[0]
        ctitle = row[1]
        uid = row[2]
        enroll_score = float(row[4] or 0)
        perf_score = user_perf.get(uid)
        if cid not in course_roi:
            course_roi[cid] = {"title": ctitle, "scores": [], "has_perf": 0, "no_perf": 0}
        if perf_score is not None:
            course_roi[cid]["scores"].append({"enrollment_score": enroll_score, "perf_score": perf_score})
            course_roi[cid]["has_perf"] += 1
        else:
            course_roi[cid]["no_perf"] += 1

    results = []
    for cid, data in course_roi.items():
        scores = data["scores"]
        n = len(scores)
        correlation = 0.0
        if n >= 3:
            mean_e = sum(s["enrollment_score"] for s in scores) / n
            mean_p = sum(s["perf_score"] for s in scores) / n
            num = sum((s["enrollment_score"] - mean_e) * (s["perf_score"] - mean_p) for s in scores)
            den_e = sum((s["enrollment_score"] - mean_e) ** 2 for s in scores) ** 0.5
            den_p = sum((s["perf_score"] - mean_p) ** 2 for s in scores) ** 0.5
            if den_e > 0 and den_p > 0:
                correlation = round(num / (den_e * den_p), 3)

        mv_info = mv_data.get(cid, {})
        results.append({
            "course_id": cid,
            "course_title": data["title"],
            "completers_with_perf_review": data["has_perf"],
            "completers_without_perf_review": data["no_perf"],
            "enrollment_vs_perf_correlation": correlation,
            "matview_completion_rate": mv_info.get("completion_rate"),
            "matview_avg_score": mv_info.get("avg_score"),
        })

    results.sort(key=lambda r: abs(r["enrollment_vs_perf_correlation"]), reverse=True)

    return {
        "courses": results,
        "total_courses_analyzed": len(results),
    }
