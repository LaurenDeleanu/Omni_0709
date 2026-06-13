from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date


# ── Vacation Requests ─────────────────────────────────────────────────────────

class VacationCreate(BaseModel):
    start_date: date
    end_date: date
    reason: Optional[str] = None
    absence_type: Optional[str] = "vacation"
    document_path: Optional[str] = None


class VacationReview(BaseModel):
    status: str  # "approved" or "rejected"


class VacationResponse(BaseModel):
    id: str
    user_id: str
    start_date: date
    end_date: date
    reason: Optional[str] = None
    status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    absence_type: Optional[str] = "vacation"
    document_path: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ── Meetings ──────────────────────────────────────────────────────────────────

class MeetingCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_datetime: datetime
    end_datetime: datetime
    location: Optional[str] = None
    attendees: List[str] = []


class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = None


class MeetingResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    start_datetime: datetime
    end_datetime: datetime
    location: Optional[str] = None
    organizer_id: str
    attendees: List[str] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Tasks ─────────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assigned_to: str
    due_date: Optional[date] = None
    priority: str = "medium"  # low, medium, high, urgent
    status: str = "todo"      # todo, in_progress, done


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[date] = None
    priority: Optional[str] = None
    status: Optional[str] = None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    assigned_to: str
    created_by: str
    due_date: Optional[date] = None
    priority: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Calendar Event (unified view) ────────────────────────────────────────────

class CalendarEvent(BaseModel):
    id: str
    type: str          # "vacation", "meeting", "task"
    title: str
    start: str         # ISO date or datetime string
    end: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    extra: Optional[dict] = None
