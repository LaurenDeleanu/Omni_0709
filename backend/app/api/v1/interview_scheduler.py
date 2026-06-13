from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from app.api.dependencies import get_tenant_db, get_current_user, require_roles
from app.models.hire import Candidate, JobPosting
from app.models.calendar import Meeting

router = APIRouter()


def _get_user_id(user_payload: dict) -> str:
    sub = user_payload.get("sub", "")
    if "|" in sub:
        return sub.split("|")[-1]
    return sub or "unknown"


class ScheduleInterviewRequest(BaseModel):
    candidate_id: str
    job_id: str
    interviewer_id: Optional[str] = None
    stage_name: str = "Phone Screen"
    scheduled_at: str
    duration_minutes: int = 60
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    notes: Optional[str] = None
    send_calendar_invite: bool = True


class InterviewSlot(BaseModel):
    date: str
    time_slots: list
    is_available: bool = True


class ScheduleInterviewResponse(BaseModel):
    interview_id: str
    calendar_event_id: Optional[str] = None
    meeting_id: Optional[str] = None
    candidate_name: str
    job_title: str
    scheduled_at: str
    location: Optional[str] = None
    meeting_link: Optional[str] = None


@router.post("/hire/schedule-interview", response_model=ScheduleInterviewResponse, status_code=status.HTTP_201_CREATED)
async def schedule_interview(
    data: ScheduleInterviewRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "recruiter", "manager"]))
):
    candidate_result = await db.execute(select(Candidate).where(Candidate.id == data.candidate_id))
    candidate = candidate_result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    job_result = await db.execute(select(JobPosting).where(JobPosting.id == data.job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    scheduled_dt = datetime.fromisoformat(data.scheduled_at)
    end_dt = scheduled_dt.replace(hour=scheduled_dt.hour + (data.duration_minutes // 60))

    candidate_name = f"{getattr(candidate, 'first_name', '')} {getattr(candidate, 'last_name', '')}".strip() or getattr(candidate, 'email', 'Unknown')
    job_title = job.title

    calendar_event = None
    meeting = None
    user_id = _get_user_id(current_user)

    if data.send_calendar_invite:
        meeting = Meeting(
            id=uuid.uuid4().hex,
            title=f"Entrevista: {candidate_name} para {job_title}",
            description=f"Entrevista de {data.stage_name} con {candidate_name} para el puesto de {job_title}\nEnlace: {data.meeting_link}",
            start_datetime=scheduled_dt,
            end_datetime=end_dt,
            location=data.location,
            organizer_id=user_id,
            attendees=[data.candidate_id, data.interviewer_id] if data.interviewer_id else [data.candidate_id]
        )
        db.add(meeting)
        await db.flush()

    candidate_slot = "interview"
    if data.stage_name:
        setattr(candidate, "stage", data.stage_name)

    if hasattr(candidate, "job_id"):
        setattr(candidate, "job_id", data.job_id)

    interview_id = uuid.uuid4().hex
    await db.commit()

    return ScheduleInterviewResponse(
        interview_id=interview_id,
        calendar_event_id=None,
        meeting_id=meeting.id if meeting else None,
        candidate_name=candidate_name,
        job_title=job_title,
        scheduled_at=data.scheduled_at,
        location=data.location,
        meeting_link=data.meeting_link,
    )


@router.get("/hire/candidate-interviews/{candidate_id}", response_model=List[ScheduleInterviewResponse])
async def get_candidate_interviews(
    candidate_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    candidate_result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = candidate_result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate_name = f"{getattr(candidate, 'first_name', '')} {getattr(candidate, 'last_name', '')}".strip() or getattr(candidate, 'email', 'Unknown')
    candidate_email = getattr(candidate, 'email', '')

    interviews = []
    if hasattr(candidate, 'email') and candidate_email:
        result = await db.execute(
            select(Meeting).where(
                Meeting.title.contains(candidate_name)
            ).order_by(Meeting.start_datetime.desc()).limit(10)
        )
        events = result.scalars().all()
        for ev in events:
            job_title = ev.title.split("para ")[-1] if "para " in ev.title else ""
            interviews.append(ScheduleInterviewResponse(
                interview_id=ev.id,
                calendar_event_id=None,
                meeting_id=ev.id,
                candidate_name=candidate_name,
                job_title=job_title,
                scheduled_at=ev.start_datetime.isoformat() if ev.start_datetime else "",
                location=ev.location,
                meeting_link=None,
            ))

    return interviews
