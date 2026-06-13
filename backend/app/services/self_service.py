import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.calendar import VacationRequest, Meeting, Task
from app.models.kudos import Kudos
from app.models.announcement import Announcement
from app.models.training import CourseEnrollment, Course
from app.models.workflow import UserWorkflow
from app.models.finance import ExpenseClaim
from app.models.grow import PerformanceReview

logger = logging.getLogger(__name__)


async def get_employee_hub(user_id: str, db: AsyncSession) -> dict:
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        return {"error": "User not found"}

    pto = await get_pto_balance(user_id, db)
    payslips = await _get_recent_payslips(user_id, db)
    pending_tasks = await _get_pending_tasks(user_id, db)
    upcoming_events = await get_upcoming_events(user_id, db, days=7)
    team = await _get_team_members(user_id, user, db)
    kudos = await _get_recent_kudos(user_id, db)
    announcements = await _get_unread_announcements(db)
    training = await _get_training_progress(user_id, db)

    return {
        "user_id": user_id,
        "pto_balance": pto,
        "recent_payslips": payslips,
        "pending_tasks": pending_tasks,
        "upcoming_events": upcoming_events,
        "team_members": team,
        "kudos_received": kudos,
        "announcements": announcements,
        "training_progress": training,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_pto_balance(user_id: str, db: AsyncSession) -> dict:
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        return {"error": "User not found"}

    req_result = await db.execute(select(VacationRequest).where(VacationRequest.user_id == user_id))
    requests = req_result.scalars().all()

    days_used = 0
    pending_requests = []
    upcoming_approved = []

    for r in requests:
        start_raw = r.start_date
        end_raw = r.end_date
        if isinstance(start_raw, datetime):
            start_raw = start_raw.date()
        if isinstance(end_raw, datetime):
            end_raw = end_raw.date()
        days = ((end_raw - start_raw).days + 1) if start_raw and end_raw else 1

        if r.status == "approved":
            days_used += days
            if r.start_date and r.start_date >= datetime.now(timezone.utc).date():
                upcoming_approved.append({
                    "id": r.id, "start_date": start_raw.isoformat(),
                    "end_date": end_raw.isoformat(), "days": days,
                })
        elif r.status == "pending":
            pending_requests.append({
                "id": r.id, "start_date": start_raw.isoformat() if start_raw else None,
                "end_date": end_raw.isoformat() if end_raw else None, "days": days,
            })

    remaining = max(0, user.vacation_allowance - days_used)

    return {
        "total_allowance": user.vacation_allowance,
        "days_used": days_used,
        "days_remaining": remaining,
        "approved_upcoming": upcoming_approved,
        "pending_requests": pending_requests,
    }


async def get_upcoming_events(user_id: str, db: AsyncSession, days: int = 7) -> list:
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days)

    meetings_result = await db.execute(
        select(Meeting).where(
            Meeting.start_datetime >= now,
            Meeting.start_datetime <= cutoff,
            Meeting.attendees.contains([user_id]),
        ).order_by(Meeting.start_datetime.asc())
    )
    meetings = meetings_result.scalars().all()

    tasks_result = await db.execute(
        select(Task).where(
            Task.assigned_to == user_id,
            Task.status.in_(["todo", "in_progress"]),
            Task.due_date <= cutoff.date() if hasattr(Task, "due_date") else True,
        ).order_by(Task.due_date.asc().nullslast())
    )
    tasks = tasks_result.scalars().all()

    reviews_result = await db.execute(
        select(PerformanceReview).where(
            PerformanceReview.employee_id == user_id,
            PerformanceReview.status != "Completed",
        )
    )
    reviews = reviews_result.scalars().all()

    events = []
    for m in meetings:
        events.append({
            "type": "meeting",
            "id": m.id,
            "title": m.title,
            "start": m.start_datetime.isoformat() if m.start_datetime else None,
            "end": m.end_datetime.isoformat() if m.end_datetime else None,
            "location": m.location,
        })
    for t in tasks:
        events.append({
            "type": "task",
            "id": t.id,
            "title": t.title,
            "priority": t.priority,
            "status": t.status,
            "due_date": t.due_date.isoformat() if t.due_date else None,
        })
    for r in reviews:
        events.append({
            "type": "performance_review",
            "id": r.id if hasattr(r, "id") else "",
            "title": f"Review: {r.cycle_name if hasattr(r, 'cycle_name') else 'Pending'}",
            "status": r.status if hasattr(r, "status") else "",
        })

    events.sort(key=lambda e: e.get("start", e.get("due_date", "")) or "")
    return events


async def _get_recent_payslips(user_id: str, db: AsyncSession) -> list:
    try:
        from sqlalchemy import text
        result = await db.execute(
            text("SELECT id, period, gross_amount, net_amount, created_at FROM payslips WHERE user_id = :uid ORDER BY created_at DESC LIMIT 3"),
            {"uid": user_id}
        )
        rows = result.fetchall()
        return [
            {"id": r[0], "period": str(r[1]), "gross_amount": float(r[2] or 0), "net_amount": float(r[3] or 0), "created_at": str(r[4])}
            for r in rows
        ]
    except Exception:
        return []


async def _get_pending_tasks(user_id: str, db: AsyncSession) -> list:
    now = datetime.now(timezone.utc)
    tasks_result = await db.execute(
        select(Task).where(
            Task.assigned_to == user_id,
            Task.status.in_(["todo", "in_progress"]),
        ).order_by(Task.priority.desc()).limit(10)
    )
    tasks = tasks_result.scalars().all()

    wf_result = await db.execute(
        select(UserWorkflow).where(UserWorkflow.user_id == user_id, UserWorkflow.status == "in_progress")
    )
    workflows = wf_result.scalars().all()

    items = []
    for t in tasks:
        items.append({
            "source": "task",
            "id": t.id,
            "title": t.title,
            "priority": t.priority,
            "status": t.status,
            "due_date": t.due_date.isoformat() if t.due_date else None,
        })
    for wf in workflows:
        pending_steps = sum(1 for s in (wf.steps_status or {}).values() if not s.get("completed"))
        items.append({
            "source": "workflow",
            "id": wf.id,
            "title": f"Workflow: {wf.template_id}",
            "pending_steps": pending_steps,
            "status": wf.status,
            "created_at": wf.created_at.isoformat() if wf.created_at else None,
        })
    return items


async def _get_team_members(user_id: str, user: User, db: AsyncSession) -> dict:
    if user.role not in ("manager", "hr_admin", "super_admin"):
        return {"is_manager": False, "members": []}

    members_result = await db.execute(
        select(User).where(User.manager_id == user_id, User.is_active == True)
    )
    members = members_result.scalars().all()

    return {
        "is_manager": True,
        "members": [
            {"id": m.id, "full_name": m.full_name, "email": m.email, "department": m.department, "role": m.role}
            for m in members
        ],
    }


async def _get_recent_kudos(user_id: str, db: AsyncSession) -> list:
    result = await db.execute(
        select(Kudos).where(Kudos.receiver_id == user_id).order_by(Kudos.created_at.desc()).limit(5)
    )
    kudos = result.scalars().all()
    items = []
    for k in kudos:
        sender_result = await db.execute(select(User).where(User.id == k.sender_id))
        sender = sender_result.scalar_one_or_none()
        items.append({
            "id": k.id,
            "sender_name": sender.full_name if sender else k.sender_id,
            "message": k.message,
            "badge": k.badge,
            "created_at": k.created_at.isoformat() if k.created_at else None,
        })
    return items


async def _get_unread_announcements(db: AsyncSession) -> list:
    result = await db.execute(
        select(Announcement).where(Announcement.is_active == True).order_by(Announcement.created_at.desc()).limit(5)
    )
    items = result.scalars().all()
    return [
        {"id": a.id, "title": a.title, "content": a.content[:300], "created_at": a.created_at.isoformat() if a.created_at else None}
        for a in items
    ]


async def _get_training_progress(user_id: str, db: AsyncSession) -> dict:
    result = await db.execute(
        select(CourseEnrollment).where(CourseEnrollment.user_id == user_id)
    )
    enrollments = result.scalars().all()

    if not enrollments:
        return {"total_enrollments": 0, "completion_pct": 0, "courses": []}

    completed = sum(1 for e in enrollments if e.status == "completed")
    total = len(enrollments)
    completion_pct = round((completed / total) * 100, 1) if total > 0 else 0

    courses = []
    for e in enrollments:
        course_result = await db.execute(select(Course).where(Course.id == e.course_id))
        course = course_result.scalar_one_or_none()
        courses.append({
            "course_id": e.course_id,
            "course_title": course.title if course else "Unknown",
            "status": e.status,
            "progress_pct": float(e.progress_percentage or 0),
            "enrolled_at": e.created_at.isoformat() if e.created_at else None,
        })

    return {
        "total_enrollments": total,
        "completed": completed,
        "completion_pct": completion_pct,
        "courses": courses,
    }
