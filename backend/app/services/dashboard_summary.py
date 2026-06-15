import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timezone, timedelta

from app.core.cache import cache_get, cache_set

logger = logging.getLogger("successcore.dashboard")

DASHCACHE_NS = "dashsummary"
DASHCACHE_TTL = 120


async def get_admin_dashboard_summary(db: AsyncSession, tenant_id: str = "default") -> Dict[str, Any]:
    cached = await cache_get(DASHCACHE_NS, tenant_id)
    if cached:
        return cached

    from app.models.user import User
    from app.models.agent import AgentExecutionRun
    from app.models.finance import ExpenseClaim
    from app.models.hire import Candidate
    from app.models.training import CourseEnrollment
    from app.models.kudos import Kudos
    from app.models.notification import Notification

    total_users_res = await db.execute(select(func.count(User.id)))
    total_users = total_users_res.scalar() or 0

    active_users_res = await db.execute(select(func.count(User.id)).where(User.is_active == True))
    active_users = active_users_res.scalar() or 0

    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    new_hires_res = await db.execute(select(func.count(User.id)).where(User.created_at >= week_ago))
    new_hires = new_hires_res.scalar() or 0

    headcount_by_dept = {}
    dept_res = await db.execute(
        select(User.department, func.count(User.id)).group_by(User.department)
    )
    headcount_by_dept["live"] = [
        {"department": r[0] or "Unassigned", "count": r[1]} for r in dept_res.fetchall()
    ]

    from app.models.pay import PayrollCycle, Payslip
    
    payroll_rows = await db.execute(
        select(
            PayrollCycle.period_name.label('month'), 
            PayrollCycle.currency, 
            PayrollCycle.total_gross, 
            PayrollCycle.total_net, 
            func.count(Payslip.id).label('payslip_count')
        )
        .outerjoin(Payslip, PayrollCycle.id == Payslip.cycle_id)
        .group_by(PayrollCycle.id)
        .order_by(PayrollCycle.start_date.desc())
        .limit(12)
    )
    payroll_summary = [
        {
            "month": str(r.month),
            "currency": r.currency,
            "total_gross": float(r.total_gross),
            "total_net": float(r.total_net),
            "payslip_count": r.payslip_count,
        }
        for r in payroll_rows.fetchall()
    ]


    from app.models.agent import Agent, AgentExecutionRun
    
    configured_agents_res = await db.execute(select(func.count(Agent.id)).where(Agent.is_active == True))
    total_configured_agents = configured_agents_res.scalar() or 0

    agent_runs_res = await db.execute(select(func.count(AgentExecutionRun.id)))
    total_agent_runs = agent_runs_res.scalar() or 0

    agent_runs_month_res = await db.execute(
        select(func.count(AgentExecutionRun.id)).where(AgentExecutionRun.created_at >= month_start)
    )
    agent_runs_month = agent_runs_month_res.scalar() or 0

    agent_success_res = await db.execute(
        select(func.count(AgentExecutionRun.id)).where(AgentExecutionRun.status == "success")
    )
    agent_success = agent_success_res.scalar() or 0

    agent_cost_res = await db.execute(
        select(func.coalesce(func.sum(AgentExecutionRun.cost_usd), 0)).where(AgentExecutionRun.created_at >= month_start)
    )
    agent_cost_month = round(agent_cost_res.scalar() or 0, 4)

    pending_expenses_res = await db.execute(
        select(func.count(ExpenseClaim.id)).where(ExpenseClaim.status == "pending")
    )
    pending_expenses = pending_expenses_res.scalar() or 0

    expense_amount_res = await db.execute(
        select(func.coalesce(func.sum(ExpenseClaim.total_amount), 0)).where(ExpenseClaim.status == "pending")
    )
    pending_expense_amount = round(expense_amount_res.scalar() or 0, 2)

    candidates_res = await db.execute(select(func.count(Candidate.id)))
    active_candidates = candidates_res.scalar() or 0

    funnel_rows = await db.execute(
        select(Candidate.stage, func.count(Candidate.id)).group_by(Candidate.stage)
    )
    hiring_funnel = {r[0]: r[1] for r in funnel_rows.fetchall()}

    enrollments_res = await db.execute(
        select(func.count(CourseEnrollment.id)).where(CourseEnrollment.status == "in_progress")
    )
    active_enrollments = enrollments_res.scalar() or 0

    training_rows = await db.execute(
        select(CourseEnrollment.course_id, func.avg(CourseEnrollment.progress_percentage)).group_by(CourseEnrollment.course_id)
    )
    training_rates = [
        {"course_id": r[0], "completion_rate": float(r[1])} for r in training_rows.fetchall()
    ]

    kudos_res = await db.execute(select(func.count(Kudos.id)).where(Kudos.created_at >= week_ago))
    kudos_week = kudos_res.scalar() or 0

    unread_notifs_res = await db.execute(
        select(func.count(Notification.id)).where(Notification.is_read == False)
    )
    unread_notifs = unread_notifs_res.scalar() or 0

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "people": {
            "total_employees": total_users,
            "active_employees": active_users,
            "new_hires_7d": new_hires,
            "headcount_by_department": headcount_by_dept["live"],
        },
        "ai_agents": {
            "total_configured_agents": total_configured_agents,
            "total_runs": total_agent_runs,
            "runs_this_month": agent_runs_month,
            "success_rate": round(agent_success / max(total_agent_runs, 1) * 100, 1),
            "cost_this_month": agent_cost_month,
        },
        "finance": {
            "pending_expenses": pending_expenses,
            "pending_expense_amount": pending_expense_amount,
            "payroll_summary": payroll_summary,
        },
        "hiring": {
            "active_candidates": active_candidates,
            "funnel_by_stage": hiring_funnel,
        },
        "training": {
            "active_enrollments": active_enrollments,
            "completion_rates": training_rates,
        },
        "engagement": {
            "kudos_7d": kudos_week,
            "unread_notifications": unread_notifs,
        },
    }

    await cache_set(DASHCACHE_NS, tenant_id, result, ttl=DASHCACHE_TTL)
    return result
