import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_, or_
from pydantic import BaseModel
from typing import Optional

from app.api.dependencies import get_tenant_db, get_current_user, require_roles
from app.models.user import User
from app.models.calendar import VacationRequest
from app.models.it import ITTicket
from app.models.hire import JobPosting, Candidate, Interview
from app.models.grow import PerformanceReview
from app.models.legal import ComplianceAudit
from app.models.training import Course, CourseEnrollment
from app.models.employee_history import EmployeeHistory

logger = logging.getLogger(__name__)
router = APIRouter()


def _require_hr_role():
    return require_roles(["hr_admin", "sys_admin"])


class ApproveBody(BaseModel):
    reviewer_note: str = ""


class RejectBody(BaseModel):
    reviewer_note: str = ""


@router.get("/overview")
async def get_hr_overview(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(_require_hr_role()),
):
    try:
        today = datetime.now(timezone.utc)
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total_emp_q = await db.execute(select(func.count()).select_from(User))
        total_employees = total_emp_q.scalar() or 0

        active_emp_q = await db.execute(
            select(func.count()).select_from(User).where(User.is_active == True)
        )
        active_employees = active_emp_q.scalar() or 0

        new_hires_q = await db.execute(
            select(func.count())
            .select_from(User)
            .where(User.hire_date >= month_start)
        )
        new_hires_month = new_hires_q.scalar() or 0

        open_jobs_q = await db.execute(
            select(func.count())
            .select_from(JobPosting)
            .where(JobPosting.status == "open")
        )
        open_jobs = open_jobs_q.scalar() or 0

        pipeline_q = await db.execute(
            select(func.count())
            .select_from(Candidate)
            .where(Candidate.stage.in_(["applied", "screening", "interview", "offer"]))
        )
        pipeline_candidates = pipeline_q.scalar() or 0

        pending_vac_q = await db.execute(
            select(func.count())
            .select_from(VacationRequest)
            .where(VacationRequest.status == "pending")
        )
        pending_time_off = pending_vac_q.scalar() or 0

        open_tickets_q = await db.execute(
            select(func.count())
            .select_from(ITTicket)
            .where(ITTicket.status.in_(["open", "in_progress"]))
        )
        open_it_tickets = open_tickets_q.scalar() or 0

        pending_reviews_q = await db.execute(
            select(func.count())
            .select_from(PerformanceReview)
            .where(PerformanceReview.status.in_(["Draft", "Self Evaluation", "Manager Evaluation"]))
        )
        upcoming_reviews = pending_reviews_q.scalar() or 0

        recent_users_q = await db.execute(
            select(
                User.id, User.full_name, User.email, User.department,
                User.role, User.hire_date, User.is_active, User.created_at,
            )
            .order_by(User.created_at.desc())
            .limit(12)
        )
        recent_activity = []
        for row in recent_users_q.all():
            record = dict(row._mapping)
            if record.get("hire_date") and isinstance(record["hire_date"], datetime):
                record["hire_date"] = record["hire_date"].isoformat()
            if record.get("created_at") and isinstance(record["created_at"], datetime):
                record["created_at"] = record["created_at"].isoformat()
            recent_activity.append(record)

        recent_hist_q = await db.execute(
            select(EmployeeHistory)
            .order_by(EmployeeHistory.created_at.desc())
            .limit(10)
        )
        history_events = []
        for h in recent_hist_q.scalars().all():
            history_events.append({
                "id": h.id,
                "employee_id": h.employee_id,
                "field_name": h.field_name,
                "old_value": h.old_value,
                "new_value": h.new_value,
                "changed_by": h.changed_by,
                "change_reason": h.change_reason,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            })

        return {
            "total_employees": total_employees,
            "active_employees": active_employees,
            "new_hires_month": new_hires_month,
            "open_jobs": open_jobs,
            "pipeline_candidates": pipeline_candidates,
            "pending_time_off": pending_time_off,
            "open_it_tickets": open_it_tickets,
            "upcoming_reviews": upcoming_reviews,
            "recent_activity": recent_activity,
            "history_events": history_events,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"HR overview error: {e}")
        return {
            "total_employees": 0, "active_employees": 0, "new_hires_month": 0,
            "open_jobs": 0, "pipeline_candidates": 0, "pending_time_off": 0,
            "open_it_tickets": 0, "upcoming_reviews": 0,
            "recent_activity": [], "history_events": [],
        }


@router.get("/tickets")
async def get_hr_tickets(
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    assignee_id: Optional[str] = Query(None, description="Filter by assignee user ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(_require_hr_role()),
):
    try:
        conditions = []
        if status:
            conditions.append(ITTicket.status == status)
        if priority:
            conditions.append(ITTicket.priority == priority)
        if assignee_id:
            conditions.append(ITTicket.assignee_id == assignee_id)

        count_q = select(func.count()).select_from(ITTicket)
        if conditions:
            count_q = count_q.where(and_(*conditions))
        total = (await db.execute(count_q)).scalar() or 0

        base_q = select(ITTicket)
        if conditions:
            base_q = base_q.where(and_(*conditions))
        base_q = base_q.order_by(ITTicket.created_at.desc()).offset(offset).limit(limit)
        results = await db.execute(base_q)
        tickets = results.scalars().all()

        items = []
        for t in tickets:
            requester_name = None
            assignee_name = None
            if t.requester_id:
                uq = await db.execute(select(User.full_name, User.email).where(User.id == t.requester_id))
                u = uq.first()
                if u:
                    requester_name = u[0] or u[1]
            if t.assignee_id:
                uq = await db.execute(select(User.full_name, User.email).where(User.id == t.assignee_id))
                u = uq.first()
                if u:
                    assignee_name = u[0] or u[1]

            items.append({
                "id": t.id,
                "title": t.title,
                "description": t.description[:200] if t.description else "",
                "category": t.category,
                "priority": t.priority,
                "status": t.status,
                "requester_id": t.requester_id,
                "requester_name": requester_name,
                "assignee_id": t.assignee_id,
                "assignee_name": assignee_name,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
            })

        return {"total": total, "limit": limit, "offset": offset, "tickets": items}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"HR tickets error: {e}")
        return {"total": 0, "limit": limit, "offset": offset, "tickets": []}


@router.get("/requests")
async def get_hr_requests(
    request_type: Optional[str] = Query(None, description="Filter: vacation, equipment, training"),
    status: Optional[str] = Query(None, description="Filter: pending, approved, rejected"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(_require_hr_role()),
):
    try:
        combined_requests = []

        vac_conditions = []
        if status:
            vac_conditions.append(VacationRequest.status == status)
        if request_type and request_type != "vacation":
            vac_q = select(func.count()).select_from(VacationRequest).where(VacationRequest.id != "x")
        vac_base = select(VacationRequest).order_by(VacationRequest.created_at.desc())
        if vac_conditions:
            vac_base = vac_base.where(and_(*vac_conditions))
        if not request_type or request_type == "vacation":
            vac_results = await db.execute(vac_base.limit(limit).offset(offset))
            for vr in vac_results.scalars().all():
                name = None
                if vr.user_id:
                    uq = await db.execute(select(User.full_name, User.email).where(User.id == vr.user_id))
                    u = uq.first()
                    if u:
                        name = u[0] or u[1]
                combined_requests.append({
                    "id": vr.id,
                    "type": "vacation",
                    "subtype": vr.absence_type or "vacation",
                    "employee_id": vr.user_id,
                    "employee_name": name,
                    "start_date": vr.start_date.isoformat() if vr.start_date else None,
                    "end_date": vr.end_date.isoformat() if vr.end_date else None,
                    "reason": vr.reason,
                    "status": vr.status,
                    "created_at": vr.created_at.isoformat() if vr.created_at else None,
                    "reviewed_by": vr.reviewed_by,
                    "reviewed_at": vr.reviewed_at.isoformat() if vr.reviewed_at else None,
                })

        combined_requests.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        total = len(combined_requests)
        sliced = combined_requests[offset:offset + limit]

        return {"total": total, "limit": limit, "offset": offset, "requests": sliced}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"HR requests error: {e}")
        return {"total": 0, "limit": limit, "offset": offset, "requests": []}


@router.get("/recruiting")
async def get_recruiting_overview(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(_require_hr_role()),
):
    try:
        job_stage_q = await db.execute(
            select(JobPosting.status, func.count(JobPosting.id))
            .group_by(JobPosting.status)
        )
        jobs_by_stage = {row[0]: row[1] for row in job_stage_q.all()}

        candidate_stage_q = await db.execute(
            select(Candidate.stage, func.count(Candidate.id))
            .group_by(Candidate.stage)
        )
        candidates_by_stage = {row[0]: row[1] for row in candidate_stage_q.all()}

        source_q = await db.execute(
            select(Candidate.source, func.count(Candidate.id))
            .where(Candidate.source != None)
            .group_by(Candidate.source)
        )
        sources = [{"source": row[0], "count": row[1]} for row in source_q.all()]

        hired_q = await db.execute(
            select(Candidate)
            .where(Candidate.stage == "hired")
        )
        hired = hired_q.scalars().all()

        total_days = 0
        hired_count = 0
        for c in hired:
            if c.created_at and c.updated_at:
                delta = c.updated_at - c.created_at
                total_days += delta.days
                hired_count += 1
        avg_time_to_hire = round(total_days / hired_count, 1) if hired_count > 0 else 0

        now = datetime.now(timezone.utc)
        month_ago = now - timedelta(days=30)
        hires_this_month_q = await db.execute(
            select(func.count())
            .select_from(Candidate)
            .where(
                and_(
                    Candidate.stage == "hired",
                    Candidate.updated_at >= month_ago,
                )
            )
        )
        hires_this_month = hires_this_month_q.scalar() or 0

        open_positions_q = await db.execute(
            select(JobPosting)
            .where(JobPosting.status == "open")
            .order_by(JobPosting.created_at.desc())
            .limit(10)
        )
        open_positions = []
        for jp in open_positions_q.scalars().all():
            cand_count_q = await db.execute(
                select(func.count()).select_from(Candidate).where(Candidate.job_id == jp.id)
            )
            cand_count = cand_count_q.scalar() or 0
            open_positions.append({
                "id": jp.id,
                "title": jp.title,
                "department": jp.department,
                "location": jp.location,
                "employment_type": jp.employment_type,
                "candidate_count": cand_count,
                "created_at": jp.created_at.isoformat() if jp.created_at else None,
            })

        return {
            "jobs_by_stage": jobs_by_stage,
            "candidates_by_stage": candidates_by_stage,
            "sources": sources,
            "avg_time_to_hire_days": avg_time_to_hire,
            "hires_this_month": hires_this_month,
            "open_positions": open_positions,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Recruiting overview error: {e}")
        return {"jobs_by_stage": {}, "candidates_by_stage": {}, "sources": [],
                "avg_time_to_hire_days": 0, "hires_this_month": 0, "open_positions": []}


@router.get("/compliance")
async def get_compliance_overview(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(_require_hr_role()),
):
    try:
        expiring_contracts_q = await db.execute(
            select(func.count())
            .select_from(User)
            .where(User.hire_date == None)
        )
        missing_contracts = expiring_contracts_q.scalar() or 0

        users_without_dept = await db.execute(
            select(func.count())
            .select_from(User)
            .where(or_(User.department == None, User.department == ""))
        )
        missing_department = users_without_dept.scalar() or 0

        total_users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
        total_users = max(total_users, 1)

        total_enrollments_q = await db.execute(
            select(func.count()).select_from(CourseEnrollment)
        )
        total_enrollments = total_enrollments_q.scalar() or 0

        completed_enrollments_q = await db.execute(
            select(func.count())
            .select_from(CourseEnrollment)
            .where(CourseEnrollment.status == "completed")
        )
        completed_enrollments = completed_enrollments_q.scalar() or 0

        training_completion_rate = round(completed_enrollments * 100.0 / total_enrollments, 1) if total_enrollments > 0 else 0

        enrolled_users_q = await db.execute(
            select(func.count(func.distinct(CourseEnrollment.user_id)))
            .select_from(CourseEnrollment)
        )
        enrolled_users = enrolled_users_q.scalar() or 0

        audits_q = await db.execute(
            select(ComplianceAudit)
            .where(ComplianceAudit.status.in_(["scheduled", "in_progress"]))
            .order_by(ComplianceAudit.scheduled_at.asc())
            .limit(10)
        )
        upcoming_audits = []
        for a in audits_q.scalars().all():
            upcoming_audits.append({
                "id": a.id,
                "title": a.title,
                "audit_type": a.audit_type,
                "status": a.status,
                "frequency": a.frequency,
                "scheduled_at": a.scheduled_at.isoformat() if a.scheduled_at else None,
            })

        now = datetime.now(timezone.utc)
        year_ago = now - timedelta(days=365)
        users_no_training_q = await db.execute(
            select(func.count())
            .select_from(User)
            .where(
                and_(
                    User.is_active == True,
                    ~User.id.in_(
                        select(CourseEnrollment.user_id).where(CourseEnrollment.created_at >= year_ago)
                    )
                )
            )
        )
        users_without_training = users_no_training_q.scalar() or 0

        return {
            "missing_contracts": missing_contracts,
            "missing_department": missing_department,
            "total_employees": total_users,
            "training_completion_rate": training_completion_rate,
            "enrolled_users": enrolled_users,
            "total_enrollments": total_enrollments,
            "completed_enrollments": completed_enrollments,
            "users_without_training": users_without_training,
            "upcoming_audits": upcoming_audits,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Compliance overview error: {e}")
        return {"missing_contracts": 0, "missing_department": 0, "total_employees": 0,
                "training_completion_rate": 0, "enrolled_users": 0, "total_enrollments": 0,
                "completed_enrollments": 0, "users_without_training": 0, "upcoming_audits": []}


@router.post("/requests/{request_id}/approve")
async def approve_request(
    request_id: str,
    body: ApproveBody = ApproveBody(),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(_require_hr_role()),
):
    try:
        vr = await db.get(VacationRequest, request_id)
        if not vr:
            raise HTTPException(status_code=404, detail="Request not found")
        if vr.status != "pending":
            raise HTTPException(status_code=400, detail="Request is not pending")

        vr.status = "approved"
        vr.reviewed_by = current_user.get("sub", "")
        vr.reviewed_at = datetime.now(timezone.utc)
        await db.commit()
        return {"success": True, "message": "Request approved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Approve request error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/requests/{request_id}/reject")
async def reject_request(
    request_id: str,
    body: RejectBody = RejectBody(),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(_require_hr_role()),
):
    try:
        vr = await db.get(VacationRequest, request_id)
        if not vr:
            raise HTTPException(status_code=404, detail="Request not found")
        if vr.status != "pending":
            raise HTTPException(status_code=400, detail="Request is not pending")

        vr.status = "rejected"
        vr.reviewed_by = current_user.get("sub", "")
        vr.reviewed_at = datetime.now(timezone.utc)
        await db.commit()
        return {"success": True, "message": "Request rejected"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Reject request error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
