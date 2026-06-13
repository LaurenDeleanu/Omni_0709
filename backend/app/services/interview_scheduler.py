import logging
import uuid
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

logger = logging.getLogger("successcore.interview_scheduler")


async def create_interview_slot(
    db: AsyncSession,
    job_id: str,
    candidate_id: str,
    interviewer_ids: List[str],
    title: str = "",
    description: str = "",
    start_datetime: Optional[str] = None,
    end_datetime: Optional[str] = None,
    duration_minutes: int = 60,
    location: str = "",
    video_link: str = "",
) -> Dict[str, Any]:
    interview_id = uuid.uuid4().hex

    if not start_datetime:
        start_dt = datetime.now(timezone.utc) + timedelta(days=2)
        start_datetime = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
    if not end_datetime:
        start_dt = datetime.fromisoformat(start_datetime)
        end_datetime = (start_dt + timedelta(minutes=duration_minutes)).strftime("%Y-%m-%dT%H:%M:%S")

    interview = {
        "id": interview_id,
        "job_id": job_id,
        "candidate_id": candidate_id,
        "interviewer_ids": interviewer_ids,
        "title": title or f"Interview with candidate",
        "description": description,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "duration_minutes": duration_minutes,
        "location": location,
        "video_link": video_link or _generate_video_link(),
        "status": "scheduled",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        from app.models.calendar import Meeting
        for interviewer_id in interviewer_ids:
            meeting = Meeting(
                id=uuid.uuid4().hex,
                title=interview["title"],
                description=interview["description"],
                organizer_id=interviewer_id,
                start_datetime=datetime.fromisoformat(start_datetime),
                end_datetime=datetime.fromisoformat(end_datetime),
                location=interview.get("video_link") or location,
                metadata={
                    "type": "interview",
                    "interview_id": interview_id,
                    "job_id": job_id,
                    "candidate_id": candidate_id,
                },
            )
            db.add(meeting)
        await db.commit()
    except Exception as e:
        logger.warning(f"Meeting creation skipped (calendar not available): {e}")

    logger.info(f"Interview slot created: {interview_id[:8]} for job={job_id[:8]} candidate={candidate_id[:8]}")
    return interview


def _generate_video_link() -> str:
    room_name = f"interview-{uuid.uuid4().hex[:8]}"
    return f"https://meet.successcore.com/{room_name}"


def generate_ics_content(interview: Dict[str, Any]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    start = datetime.fromisoformat(interview["start_datetime"]).strftime("%Y%m%dT%H%M%SZ")
    end = datetime.fromisoformat(interview["end_datetime"]).strftime("%Y%m%dT%H%M%SZ")

    return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//SuccessCore//Interview Scheduler//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
DTSTART:{start}
DTEND:{end}
DTSTAMP:{now}
ORGANIZER;CN=SuccessCore HR:mailto:hr@successcore.com
UID:{interview.get('id', '')}@successcore.com
SUMMARY:{interview.get('title', 'Interview')}
DESCRIPTION:{interview.get('description', '')}\nVideo link: {interview.get('video_link', '')}
LOCATION:{interview.get('video_link', interview.get('location', 'Online'))}
STATUS:CONFIRMED
SEQUENCE:0
BEGIN:VALARM
TRIGGER:-PT30M
ACTION:DISPLAY
DESCRIPTION:Reminder: Interview in 30 minutes
END:VALARM
END:VEVENT
END:VCALENDAR"""


async def get_available_slots(
    db: AsyncSession,
    interviewer_id: str,
    start_date: str,
    end_date: str,
) -> List[Dict[str, Any]]:
    hours = [9, 10, 11, 12, 13, 14, 15, 16, 17]
    start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
    end_dt = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)

    existing_meetings = set()
    try:
        from app.models.calendar import Meeting
        result = await db.execute(
            select(Meeting).where(
                and_(
                    Meeting.organizer_id == interviewer_id,
                    Meeting.start_datetime >= start_dt,
                    Meeting.end_datetime <= end_dt,
                )
            )
        )
        for meeting in result.scalars().all():
            day = meeting.start_datetime.date().isoformat()
            hour = meeting.start_datetime.hour
            existing_meetings.add(f"{day}:{hour}")
    except Exception:
        pass

    slots = []
    current = start_dt
    while current <= end_dt:
        if current.weekday() < 5:
            for hour in hours:
                slot_key = f"{current.date().isoformat()}:{hour}"
                if slot_key not in existing_meetings:
                    slot_start = current.replace(hour=hour, minute=0, second=0)
                    slot_end = slot_start + timedelta(hours=1)
                    slots.append({
                        "datetime": slot_start.isoformat(),
                        "end_datetime": slot_end.isoformat(),
                        "available": True,
                    })
        current += timedelta(days=1)

    return slots[:50]


def generate_interview_email(interview: Dict[str, Any], candidate_name: str = "", candidate_email: str = "") -> Dict[str, str]:
    start_dt = datetime.fromisoformat(interview["start_datetime"])
    date_str = start_dt.strftime("%d de %B de %Y")
    time_str = start_dt.strftime("%H:%M")

    subject = f"Entrevista confirmada: {interview.get('title', '')}"
    body = f"""Hola {candidate_name or 'candidato/a'},

Tu entrevista ha sido confirmada para el {date_str} a las {time_str} horas.

Duración estimada: {interview.get('duration_minutes', 60)} minutos
Enlace de videollamada: {interview.get('video_link', interview.get('location', 'Online'))}

Por favor, confirma tu asistencia o contacta con RRHH si necesitas cambiar la fecha.

Saludos,
Equipo de SuccessCore HR"""

    return {"subject": subject, "body": body, "to": candidate_email}
