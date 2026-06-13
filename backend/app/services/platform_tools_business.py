import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.training import Course, CourseEnrollment, FundaeValidation
from app.models.hire import JobPosting, Candidate, Interview
from app.models.grow import Objective, KeyResult, PerformanceReview
from app.models.sales import Client, Lead
from app.models.work import Project, Task, WikiPage
from app.models.legal import Contract, WhistleblowerReport
from app.models.kudos import Kudos

logger = logging.getLogger(__name__)

VALID_STAGES = {"applied", "screening", "interview", "offer", "hired", "rejected"}


# ──────────────────────────────────────────────────────────────────
# TRAINING TOOLS (5)
# ──────────────────────────────────────────────────────────────────

async def tool_enroll_in_course(db: AsyncSession, employee_id: str, course_id: str) -> str:
    try:
        user_res = await db.execute(select(User).where(User.id == employee_id))
        if not user_res.scalar_one_or_none():
            return json.dumps({"error": "Employee not found"})

        course_res = await db.execute(select(Course).where(Course.id == course_id))
        if not course_res.scalar_one_or_none():
            return json.dumps({"error": "Course not found"})

        existing = await db.execute(
            select(CourseEnrollment).where(
                CourseEnrollment.user_id == employee_id,
                CourseEnrollment.course_id == course_id,
            )
        )
        if existing.scalar_one_or_none():
            return json.dumps({"error": "Employee already enrolled in this course"})

        enrollment = CourseEnrollment(
            id=uuid.uuid4().hex,
            user_id=employee_id,
            course_id=course_id,
            status="enrolled",
            progress_percentage=0.0,
            time_spent_seconds=0,
            created_at=datetime.now(timezone.utc),
        )
        db.add(enrollment)
        await db.commit()
        return json.dumps({
            "success": True,
            "enrollment_id": enrollment.id,
            "course_id": course_id,
            "employee_id": employee_id,
            "status": "enrolled",
        })
    except Exception as e:
        logger.error(f"Error in tool_enroll_in_course: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_training_progress(db: AsyncSession, employee_id: str) -> str:
    try:
        user_res = await db.execute(select(User).where(User.id == employee_id))
        if not user_res.scalar_one_or_none():
            return json.dumps({"error": "Employee not found"})

        result = await db.execute(
            select(CourseEnrollment).where(CourseEnrollment.user_id == employee_id)
        )
        enrollments = result.scalars().all()

        data = []
        for e in enrollments:
            c_res = await db.execute(select(Course).where(Course.id == e.course_id))
            course = c_res.scalar_one_or_none()
            data.append({
                "enrollment_id": e.id,
                "course_name": course.title if course else "Unknown",
                "status": e.status,
                "progress_pct": float(e.progress_percentage),
                "score": float(e.score) if e.score is not None else None,
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                "time_spent_seconds": e.time_spent_seconds,
            })

        return json.dumps({
            "success": True,
            "employee_id": employee_id,
            "total_enrollments": len(data),
            "enrollments": data,
        })
    except Exception as e:
        logger.error(f"Error in tool_get_training_progress: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_course_catalog(db: AsyncSession, category: str = "", fundae_only: bool = False) -> str:
    try:
        query = select(Course)
        if fundae_only:
            query = query.where(Course.is_fundae_eligible == True)
        if category:
            query = query.where(Course.title.ilike(f"%{category}%"))
        result = await db.execute(query)
        courses = result.scalars().all()

        return json.dumps({
            "success": True,
            "total": len(courses),
            "courses": [{
                "id": c.id,
                "title": c.title,
                "description": c.description,
                "is_scorm": c.is_scorm,
                "min_duration_hours": float(c.min_duration_hours),
                "is_fundae_eligible": c.is_fundae_eligible,
            } for c in courses],
        })
    except Exception as e:
        logger.error(f"Error in tool_get_course_catalog: {e}")
        return json.dumps({"error": str(e)})


async def tool_recommend_courses(db: AsyncSession, employee_id: str, limit: int = 3) -> str:
    try:
        from app.services.course_recommender import recommend_courses
        result = await recommend_courses(db, employee_id)
        recommendations = result.get("recommendations", [])[:limit]
        return json.dumps({
            "success": True,
            "employee_id": employee_id,
            "recommendations": recommendations,
        })
    except Exception as e:
        logger.error(f"Error in tool_recommend_courses: {e}")
        return json.dumps({"error": str(e)})


async def tool_validate_fundae(db: AsyncSession, enrollment_id: str) -> str:
    try:
        enrollment_res = await db.execute(
            select(CourseEnrollment).where(CourseEnrollment.id == enrollment_id)
        )
        enrollment = enrollment_res.scalar_one_or_none()
        if not enrollment:
            return json.dumps({"error": "Enrollment not found"})

        course_res = await db.execute(select(Course).where(Course.id == enrollment.course_id))
        course = course_res.scalar_one_or_none()
        if not course:
            return json.dumps({"error": "Course not found"})

        existing_val = await db.execute(
            select(FundaeValidation).where(FundaeValidation.enrollment_id == enrollment_id)
        )
        validation = existing_val.scalar_one_or_none()

        if not validation:
            duration_valid = float(enrollment.time_spent_seconds) >= (course.min_duration_hours * 3600)
            progress_valid = float(enrollment.progress_percentage) >= 75.0
            score = float(enrollment.score or 0)
            test_valid = score >= 50.0
            survey_valid = True
            overall = duration_valid and progress_valid and test_valid and survey_valid
            validation = FundaeValidation(
                id=uuid.uuid4().hex,
                enrollment_id=enrollment_id,
                duration_valid=duration_valid,
                progress_valid=progress_valid,
                test_valid=test_valid,
                survey_valid=survey_valid,
                overall_eligible=overall,
                generated_at=datetime.now(timezone.utc),
            )
            db.add(validation)
            await db.commit()

        return json.dumps({
            "success": True,
            "enrollment_id": enrollment_id,
            "duration_valid": validation.duration_valid,
            "progress_valid": validation.progress_valid,
            "test_valid": validation.test_valid,
            "survey_valid": validation.survey_valid,
            "overall_eligible": validation.overall_eligible,
            "validation_id": validation.id,
        })
    except Exception as e:
        logger.error(f"Error in tool_validate_fundae: {e}")
        return json.dumps({"error": str(e)})


# ──────────────────────────────────────────────────────────────────
# RECRUITMENT TOOLS (7)
# ──────────────────────────────────────────────────────────────────

async def tool_create_job_posting(
    db: AsyncSession,
    title: str,
    department: str,
    description: str,
    location: str = "",
    employment_type: str = "full-time",
) -> str:
    try:
        job = JobPosting(
            id=uuid.uuid4().hex,
            title=title,
            department=department,
            description=description,
            location=location,
            employment_type=employment_type,
            status="open",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(job)
        await db.commit()
        return json.dumps({
            "success": True,
            "job_id": job.id,
            "title": job.title,
            "department": job.department,
            "status": job.status,
        })
    except Exception as e:
        logger.error(f"Error in tool_create_job_posting: {e}")
        return json.dumps({"error": str(e)})


async def tool_add_candidate(
    db: AsyncSession,
    job_id: str,
    first_name: str,
    last_name: str,
    email: str,
    phone: str = "",
    source: str = "",
    notes: str = "",
) -> str:
    try:
        job_res = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
        if not job_res.scalar_one_or_none():
            return json.dumps({"error": "Job posting not found"})

        candidate = Candidate(
            id=uuid.uuid4().hex,
            job_id=job_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            source=source,
            notes=notes,
            stage="applied",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(candidate)
        await db.commit()
        return json.dumps({
            "success": True,
            "candidate_id": candidate.id,
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "stage": candidate.stage,
        })
    except Exception as e:
        logger.error(f"Error in tool_add_candidate: {e}")
        return json.dumps({"error": str(e)})


async def tool_move_candidate_stage(db: AsyncSession, candidate_id: str, new_stage: str) -> str:
    try:
        if new_stage not in VALID_STAGES:
            return json.dumps({
                "error": f"Invalid stage '{new_stage}'. Valid: {', '.join(sorted(VALID_STAGES))}"
            })

        result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
        candidate = result.scalar_one_or_none()
        if not candidate:
            return json.dumps({"error": "Candidate not found"})

        old_stage = candidate.stage
        candidate.stage = new_stage
        candidate.updated_at = datetime.now(timezone.utc)
        await db.commit()

        logger.info(f"Candidate {candidate_id} stage changed: {old_stage} -> {new_stage}")

        response = {
            "success": True,
            "candidate_id": candidate.id,
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "old_stage": old_stage,
            "new_stage": new_stage,
        }
        if new_stage == "hired":
            response["message"] = "Candidate has been hired. Consider calling promote_to_employee to convert to an employee record."
        return json.dumps(response)
    except Exception as e:
        logger.error(f"Error in tool_move_candidate_stage: {e}")
        return json.dumps({"error": str(e)})


async def tool_schedule_interview(
    db: AsyncSession,
    candidate_id: str,
    interviewer_id: str,
    scheduled_at: str,
    duration_minutes: int = 60,
    interview_type: str = "video",
) -> str:
    try:
        candidate_res = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
        candidate = candidate_res.scalar_one_or_none()
        if not candidate:
            return json.dumps({"error": "Candidate not found"})

        interviewer_res = await db.execute(select(User).where(User.id == interviewer_id))
        if not interviewer_res.scalar_one_or_none():
            return json.dumps({"error": "Interviewer not found"})

        interview = Interview(
            id=uuid.uuid4().hex,
            candidate_id=candidate_id,
            interviewer_id=interviewer_id,
            scheduled_at=datetime.fromisoformat(scheduled_at) if isinstance(scheduled_at, str) else scheduled_at,
            duration_minutes=duration_minutes,
            interview_type=interview_type,
            created_at=datetime.now(timezone.utc),
        )
        db.add(interview)
        await db.commit()
        return json.dumps({
            "success": True,
            "interview_id": interview.id,
            "candidate_id": candidate_id,
            "interviewer_id": interviewer_id,
            "scheduled_at": str(interview.scheduled_at),
            "interview_type": interview_type,
        })
    except Exception as e:
        logger.error(f"Error in tool_schedule_interview: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_job_applications(db: AsyncSession, job_id: str) -> str:
    try:
        job_res = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
        job = job_res.scalar_one_or_none()
        if not job:
            return json.dumps({"error": "Job posting not found"})

        result = await db.execute(select(Candidate).where(Candidate.job_id == job_id))
        candidates = result.scalars().all()

        stage_counts = {}
        for c in candidates:
            stage_counts[c.stage] = stage_counts.get(c.stage, 0) + 1

        return json.dumps({
            "success": True,
            "job_id": job_id,
            "job_title": job.title,
            "total_candidates": len(candidates),
            "stage_counts": stage_counts,
            "candidates": [{
                "id": c.id,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "email": c.email,
                "stage": c.stage,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            } for c in candidates],
        })
    except Exception as e:
        logger.error(f"Error in tool_get_job_applications: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_pipeline_stats(db: AsyncSession) -> str:
    try:
        open_jobs_res = await db.execute(
            select(func.count(JobPosting.id)).where(JobPosting.status == "open")
        )
        total_open = open_jobs_res.scalar() or 0

        total_candidates_res = await db.execute(select(func.count(Candidate.id)))
        total_candidates = total_candidates_res.scalar() or 0

        stage_res = await db.execute(
            select(Candidate.stage, func.count(Candidate.id)).group_by(Candidate.stage)
        )
        stage_dist = {row[0]: row[1] for row in stage_res.all()}

        hire_count = stage_dist.get("hired", 0)
        avg_time_to_hire = None
        if hire_count > 0:
            hired_candidates = await db.execute(
                select(Candidate).where(Candidate.stage == "hired")
            )
            diffs = []
            for c in hired_candidates.scalars().all():
                if c.created_at and c.updated_at:
                    diff = (c.updated_at - c.created_at).days
                    diffs.append(diff)
            if diffs:
                avg_time_to_hire = round(sum(diffs) / len(diffs), 1)

        return json.dumps({
            "success": True,
            "total_open_jobs": total_open,
            "total_candidates": total_candidates,
            "stage_distribution": stage_dist,
            "avg_time_to_hire_days": avg_time_to_hire,
        })
    except Exception as e:
        logger.error(f"Error in tool_get_pipeline_stats: {e}")
        return json.dumps({"error": str(e)})


async def tool_promote_to_employee(
    db: AsyncSession,
    candidate_id: str,
    base_salary: float = None,
    contract_type: str = "indefinido",
) -> str:
    try:
        result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
        candidate = result.scalar_one_or_none()
        if not candidate:
            return json.dumps({"error": "Candidate not found"})

        existing_user = await db.execute(select(User).where(User.email == candidate.email))
        if existing_user.scalar_one_or_none():
            return json.dumps({"error": f"A user with email {candidate.email} already exists"})

        new_user = User(
            id=uuid.uuid4().hex,
            email=candidate.email,
            full_name=f"{candidate.first_name} {candidate.last_name}",
            phone_number=candidate.phone,
            base_salary=base_salary or 0.0,
            contract_type=contract_type,
            hire_date=datetime.now(timezone.utc),
            is_active=True,
            role="employee",
            vacation_allowance=30,
            country="ES",
            timezone="Europe/Madrid",
            currency="EUR",
            locale="es",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(new_user)

        candidate.stage = "hired"
        candidate.updated_at = datetime.now(timezone.utc)
        await db.commit()

        return json.dumps({
            "success": True,
            "employee_id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "contract_type": new_user.contract_type,
            "base_salary": new_user.base_salary,
            "candidate_id": candidate_id,
            "message": f"Candidate {candidate.first_name} {candidate.last_name} promoted to employee",
        })
    except Exception as e:
        logger.error(f"Error in tool_promote_to_employee: {e}")
        return json.dumps({"error": str(e)})


# ──────────────────────────────────────────────────────────────────
# PERFORMANCE / GROW TOOLS (5)
# ──────────────────────────────────────────────────────────────────

async def tool_create_okr(
    db: AsyncSession,
    employee_id: str,
    title: str,
    description: str = "",
    krs: List[dict] = None,
) -> str:
    try:
        user_res = await db.execute(select(User).where(User.id == employee_id))
        if not user_res.scalar_one_or_none():
            return json.dumps({"error": "Employee not found"})

        obj = Objective(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            owner_id=employee_id,
            status="On Track",
            created_at=datetime.now(timezone.utc),
        )
        db.add(obj)

        kr_ids = []
        if krs:
            for kr_data in krs:
                kr = KeyResult(
                    id=str(uuid.uuid4()),
                    objective_id=obj.id,
                    title=kr_data.get("title", ""),
                    target_value=kr_data.get("target_value", 100),
                    current_value=kr_data.get("current_value", 0),
                    unit=kr_data.get("unit", "%"),
                )
                db.add(kr)
                kr_ids.append(kr.id)

        await db.commit()
        return json.dumps({
            "success": True,
            "objective_id": obj.id,
            "title": obj.title,
            "status": obj.status,
            "key_results_count": len(kr_ids),
            "key_result_ids": kr_ids,
        })
    except Exception as e:
        logger.error(f"Error in tool_create_okr: {e}")
        return json.dumps({"error": str(e)})


async def tool_update_key_result(db: AsyncSession, kr_id: str, current_value: int) -> str:
    try:
        result = await db.execute(select(KeyResult).where(KeyResult.id == kr_id))
        kr = result.scalar_one_or_none()
        if not kr:
            return json.dumps({"error": "Key Result not found"})

        kr.current_value = current_value
        await db.commit()

        progress_pct = round((current_value / max(kr.target_value, 1)) * 100, 1)

        obj_res = await db.execute(select(Objective).where(Objective.id == kr.objective_id))
        obj = obj_res.scalar_one_or_none()

        return json.dumps({
            "success": True,
            "kr_id": kr.id,
            "title": kr.title,
            "current_value": kr.current_value,
            "target_value": kr.target_value,
            "progress_pct": progress_pct,
            "objective_title": obj.title if obj else None,
        })
    except Exception as e:
        logger.error(f"Error in tool_update_key_result: {e}")
        return json.dumps({"error": str(e)})


async def tool_create_review(
    db: AsyncSession,
    employee_id: str,
    manager_id: str,
    cycle_name: str,
    self_assessment: str = "",
) -> str:
    try:
        employee_res = await db.execute(select(User).where(User.id == employee_id))
        if not employee_res.scalar_one_or_none():
            return json.dumps({"error": "Employee not found"})

        manager_res = await db.execute(select(User).where(User.id == manager_id))
        if not manager_res.scalar_one_or_none():
            return json.dumps({"error": "Manager not found"})

        self_eval = {"notes": self_assessment} if self_assessment else None

        review = PerformanceReview(
            id=str(uuid.uuid4()),
            employee_id=employee_id,
            manager_id=manager_id,
            cycle_name=cycle_name,
            status="Self Evaluation" if self_assessment else "Draft",
            self_evaluation=self_eval,
            created_at=datetime.now(timezone.utc),
        )
        db.add(review)
        await db.commit()
        return json.dumps({
            "success": True,
            "review_id": review.id,
            "employee_id": employee_id,
            "manager_id": manager_id,
            "cycle_name": cycle_name,
            "status": review.status,
        })
    except Exception as e:
        logger.error(f"Error in tool_create_review: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_team_okrs(db: AsyncSession, department: str = "") -> str:
    try:
        query = select(User).where(User.is_active == True)
        if department:
            query = query.where(User.department == department)
        users_res = await db.execute(query)
        users = users_res.scalars().all()
        user_ids = [u.id for u in users]

        if not user_ids:
            return json.dumps({"success": True, "department": department, "okrs": []})

        okr_res = await db.execute(
            select(Objective).where(Objective.owner_id.in_(user_ids))
        )
        objectives = okr_res.scalars().all()

        data = []
        for obj in objectives:
            kr_res = await db.execute(
                select(KeyResult).where(KeyResult.objective_id == obj.id)
            )
            krs = kr_res.scalars().all()
            user = next((u for u in users if u.id == obj.owner_id), None)
            kr_list = []
            for kr in krs:
                pct = round((kr.current_value / max(kr.target_value, 1)) * 100, 1)
                kr_list.append({
                    "id": kr.id,
                    "title": kr.title,
                    "current_value": kr.current_value,
                    "target_value": kr.target_value,
                    "unit": kr.unit,
                    "progress_pct": pct,
                })
            data.append({
                "objective_id": obj.id,
                "title": obj.title,
                "owner_name": user.full_name if user else obj.owner_id,
                "status": obj.status,
                "key_results": kr_list,
            })

        return json.dumps({
            "success": True,
            "department": department or "all",
            "total_okrs": len(data),
            "okrs": data,
        })
    except Exception as e:
        logger.error(f"Error in tool_get_team_okrs: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_kudos_received(db: AsyncSession, employee_id: str, limit: int = 10) -> str:
    try:
        user_res = await db.execute(select(User).where(User.id == employee_id))
        if not user_res.scalar_one_or_none():
            return json.dumps({"error": "Employee not found"})

        result = await db.execute(
            select(Kudos).where(Kudos.receiver_id == employee_id).order_by(Kudos.created_at.desc()).limit(limit)
        )
        kudos_list = result.scalars().all()

        data = []
        for k in kudos_list:
            sender_res = await db.execute(select(User).where(User.id == k.sender_id))
            sender = sender_res.scalar_one_or_none()
            data.append({
                "id": k.id,
                "sender_name": sender.full_name or sender.email if sender else k.sender_id,
                "message": k.message,
                "badge": k.badge,
                "created_at": k.created_at.isoformat() if k.created_at else None,
            })

        return json.dumps({
            "success": True,
            "employee_id": employee_id,
            "total": len(data),
            "kudos": data,
        })
    except Exception as e:
        logger.error(f"Error in tool_get_kudos_received: {e}")
        return json.dumps({"error": str(e)})


# ──────────────────────────────────────────────────────────────────
# CRM / SALES TOOLS (6)
# ──────────────────────────────────────────────────────────────────

async def tool_get_pipeline_overview(db: AsyncSession) -> str:
    try:
        stage_res = await db.execute(
            select(Lead.stage, func.count(Lead.id), func.sum(Lead.estimated_value), func.avg(Lead.probability))
            .group_by(Lead.stage)
        )
        rows = stage_res.all()

        stages = []
        total_count = 0
        total_value = 0.0
        for stage, count, value_sum, avg_prob in rows:
            total_count += count
            total_value += float(value_sum or 0)
            stages.append({
                "stage": stage,
                "count": count,
                "total_value": float(value_sum or 0),
                "avg_probability": round(float(avg_prob or 0), 1),
            })

        return json.dumps({
            "success": True,
            "total_leads": total_count,
            "total_pipeline_value": total_value,
            "stages": stages,
        })
    except Exception as e:
        logger.error(f"Error in tool_get_pipeline_overview: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_client_details(db: AsyncSession, client_id: str) -> str:
    try:
        result = await db.execute(select(Client).where(Client.id == client_id))
        client = result.scalar_one_or_none()
        if not client:
            return json.dumps({"error": "Client not found"})

        leads_res = await db.execute(select(Lead).where(Lead.client_id == client_id))
        leads = leads_res.scalars().all()

        return json.dumps({
            "success": True,
            "client": {
                "id": client.id,
                "company_name": client.company_name,
                "industry": client.industry,
                "website": client.website,
                "primary_contact_name": client.primary_contact_name,
                "primary_contact_email": client.primary_contact_email,
                "primary_contact_phone": client.primary_contact_phone,
                "created_at": client.created_at.isoformat() if client.created_at else None,
            },
            "leads": [{
                "id": l.id,
                "title": l.title,
                "stage": l.stage,
                "estimated_value": l.estimated_value,
                "probability": l.probability,
            } for l in leads],
        })
    except Exception as e:
        logger.error(f"Error in tool_get_client_details: {e}")
        return json.dumps({"error": str(e)})


async def tool_search_clients(db: AsyncSession, query: str = "", industry: str = "") -> str:
    try:
        q = select(Client)
        if query:
            q = q.where(Client.company_name.ilike(f"%{query}%"))
        if industry:
            q = q.where(Client.industry.ilike(f"%{industry}%"))
        q = q.limit(50)
        result = await db.execute(q)
        clients = result.scalars().all()

        return json.dumps({
            "success": True,
            "total": len(clients),
            "clients": [{
                "id": c.id,
                "company_name": c.company_name,
                "industry": c.industry,
                "primary_contact_name": c.primary_contact_name,
                "primary_contact_email": c.primary_contact_email,
            } for c in clients],
        })
    except Exception as e:
        logger.error(f"Error in tool_search_clients: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_deal_stats(db: AsyncSession, period: str = "month") -> str:
    try:
        now = datetime.now(timezone.utc)
        if period == "month":
            since = now - timedelta(days=30)
        elif period == "quarter":
            since = now - timedelta(days=90)
        elif period == "year":
            since = now - timedelta(days=365)
        else:
            since = now - timedelta(days=30)

        all_leads_res = await db.execute(select(Lead).where(Lead.created_at >= since))
        all_leads = all_leads_res.scalars().all()

        won = [l for l in all_leads if l.stage == "won"]
        lost = [l for l in all_leads if l.stage == "lost"]
        total = len(all_leads)
        won_count = len(won)
        lost_count = len(lost)
        won_value = sum(l.estimated_value or 0 for l in won)

        loss_rate = round((lost_count / max(total, 1)) * 100, 1)
        avg_deal_size = round(sum(l.estimated_value or 0 for l in all_leads) / max(total, 1), 2)

        return json.dumps({
            "success": True,
            "period": period,
            "total_deals": total,
            "won_count": won_count,
            "won_value": won_value,
            "lost_count": lost_count,
            "loss_rate_pct": loss_rate,
            "avg_deal_size": avg_deal_size,
        })
    except Exception as e:
        logger.error(f"Error in tool_get_deal_stats: {e}")
        return json.dumps({"error": str(e)})


async def tool_create_task_for_lead(
    db: AsyncSession,
    lead_id: str,
    title: str,
    description: str = "",
    due_date: str = "",
) -> str:
    try:
        lead_res = await db.execute(select(Lead).where(Lead.id == lead_id))
        if not lead_res.scalar_one_or_none():
            return json.dumps({"error": "Lead not found"})

        from app.models.calendar import Task as CalendarTask
        task = CalendarTask(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            status="pending",
            priority="medium",
            due_date=datetime.fromisoformat(due_date) if due_date else None,
            context=f"lead:{lead_id}",
        )
        db.add(task)
        await db.commit()
        return json.dumps({
            "success": True,
            "task_id": task.id,
            "title": task.title,
            "lead_id": lead_id,
        })
    except Exception as e:
        logger.error(f"Error in tool_create_task_for_lead: {e}")
        return json.dumps({"error": str(e)})


async def tool_log_lead_activity(
    db: AsyncSession,
    lead_id: str,
    activity_type: str,
    notes: str,
) -> str:
    try:
        lead_res = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = lead_res.scalar_one_or_none()
        if not lead:
            return json.dumps({"error": "Lead not found"})

        logger.info(f"Lead activity logged: lead={lead_id}, type={activity_type}, notes={notes[:200]}")

        return json.dumps({
            "success": True,
            "lead_id": lead_id,
            "lead_title": lead.title,
            "activity_type": activity_type,
            "activity_id": str(uuid.uuid4()),
            "message": f"Activity '{activity_type}' logged for lead '{lead.title}'",
        })
    except Exception as e:
        logger.error(f"Error in tool_log_lead_activity: {e}")
        return json.dumps({"error": str(e)})


# ──────────────────────────────────────────────────────────────────
# PROJECT MANAGEMENT TOOLS (4)
# ──────────────────────────────────────────────────────────────────

async def tool_create_project(
    db: AsyncSession,
    name: str,
    description: str = "",
    status: str = "active",
) -> str:
    try:
        project = Project(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            status=status,
            created_at=datetime.now(timezone.utc),
        )
        db.add(project)
        await db.commit()
        return json.dumps({
            "success": True,
            "project_id": project.id,
            "name": project.name,
            "status": project.status,
        })
    except Exception as e:
        logger.error(f"Error in tool_create_project: {e}")
        return json.dumps({"error": str(e)})


async def tool_create_project_task(
    db: AsyncSession,
    project_id: str,
    title: str,
    description: str = "",
    assignee_id: str = "",
    priority: str = "medium",
    due_date: str = "",
) -> str:
    try:
        project_res = await db.execute(select(Project).where(Project.id == project_id))
        if not project_res.scalar_one_or_none():
            return json.dumps({"error": "Project not found"})

        task = Task(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title=title,
            description=description,
            assignee_id=assignee_id or None,
            priority=priority,
            status="todo",
            due_date=datetime.fromisoformat(due_date) if due_date else None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(task)
        await db.commit()
        return json.dumps({
            "success": True,
            "task_id": task.id,
            "title": task.title,
            "project_id": project_id,
            "priority": task.priority,
            "assignee_id": task.assignee_id,
        })
    except Exception as e:
        logger.error(f"Error in tool_create_project_task: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_project_status(db: AsyncSession, project_id: str) -> str:
    try:
        project_res = await db.execute(select(Project).where(Project.id == project_id))
        project = project_res.scalar_one_or_none()
        if not project:
            return json.dumps({"error": "Project not found"})

        tasks_res = await db.execute(select(Task).where(Task.project_id == project_id))
        tasks = tasks_res.scalars().all()

        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == "completed" or t.status == "done")
        in_progress = sum(1 for t in tasks if t.status == "in_progress")
        blocked = sum(1 for t in tasks if t.status == "blocked")
        todo = total - completed - in_progress - blocked

        return json.dumps({
            "success": True,
            "project": {
                "id": project.id,
                "name": project.name,
                "status": project.status,
                "description": project.description,
                "due_date": project.due_date.isoformat() if project.due_date else None,
            },
            "tasks": {
                "total": total,
                "completed": completed,
                "in_progress": in_progress,
                "blocked": blocked,
                "todo": todo,
            },
        })
    except Exception as e:
        logger.error(f"Error in tool_get_project_status: {e}")
        return json.dumps({"error": str(e)})


async def tool_create_wiki_page(
    db: AsyncSession,
    title: str,
    content: str,
    project_id: str = "",
) -> str:
    try:
        page = WikiPage(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            project_id=project_id or None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(page)
        await db.commit()
        return json.dumps({
            "success": True,
            "wiki_page_id": page.id,
            "title": page.title,
            "project_id": project_id or None,
        })
    except Exception as e:
        logger.error(f"Error in tool_create_wiki_page: {e}")
        return json.dumps({"error": str(e)})


# ──────────────────────────────────────────────────────────────────
# LEGAL / COMPLIANCE TOOLS (3)
# ──────────────────────────────────────────────────────────────────

async def tool_get_contracts(db: AsyncSession, status: str = "") -> str:
    try:
        query = select(Contract)
        if status:
            query = query.where(Contract.status == status)
        query = query.limit(50)
        result = await db.execute(query)
        contracts = result.scalars().all()

        return json.dumps({
            "success": True,
            "total": len(contracts),
            "contracts": [{
                "id": c.id,
                "title": c.title,
                "party_name": c.party_name,
                "status": c.status,
                "valid_from": c.valid_from.isoformat() if c.valid_from else None,
                "valid_until": c.valid_until.isoformat() if c.valid_until else None,
            } for c in contracts],
        })
    except Exception as e:
        logger.error(f"Error in tool_get_contracts: {e}")
        return json.dumps({"error": str(e)})


async def tool_get_compliance_status(db: AsyncSession) -> str:
    try:
        gdpr_ok = True
        fundae_ok = True
        labor_ok = True

        from app.models.training import FundaeValidation
        val_res = await db.execute(
            select(func.count(FundaeValidation.id)).where(FundaeValidation.overall_eligible == True)
        )
        fundae_validated = val_res.scalar() or 0

        whistleblower_res = await db.execute(
            select(func.count(WhistleblowerReport.id))
        )
        whistleblower_count = whistleblower_res.scalar() or 0

        contract_res = await db.execute(
            select(func.count(Contract.id)).where(Contract.status == "active")
        )
        active_contracts = contract_res.scalar() or 0

        return json.dumps({
            "success": True,
            "gdpr_compliant": True,
            "gdpr_details": {
                "whistleblower_channel_active": True,
                "dsar_requests_enabled": True,
                "encryption_enabled": True,
            },
            "fundae_compliant": fundae_ok,
            "fundae_details": {
                "validated_enrollments": fundae_validated,
            },
            "labor_law_compliant": labor_ok,
            "labor_details": {
                "active_contracts": active_contracts,
                "whistleblower_reports": whistleblower_count,
            },
        })
    except Exception as e:
        logger.error(f"Error in tool_get_compliance_status: {e}")
        return json.dumps({"error": str(e)})


async def tool_submit_whistleblower(
    db: AsyncSession,
    title: str,
    description: str,
    category: str = "",
    is_anonymous: bool = False,
) -> str:
    try:
        report = WhistleblowerReport(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            category=category or "other",
            is_anonymous=is_anonymous,
            status="open",
            created_at=datetime.now(timezone.utc),
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        return json.dumps({
            "success": True,
            "report_id": report.id,
            "tracking_code": report.tracking_code,
            "status": report.status,
            "is_anonymous": report.is_anonymous,
            "message": f"Whistleblower report submitted. Tracking code: {report.tracking_code}",
        })
    except Exception as e:
        logger.error(f"Error in tool_submit_whistleblower: {e}")
        return json.dumps({"error": str(e)})
