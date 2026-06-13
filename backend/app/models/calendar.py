from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Date, Text, ForeignKey, JSON
from datetime import datetime, timezone, date
import uuid
from app.models.base import Base


class VacationRequest(Base):
    """
    Solicitud de vacaciones de un empleado dentro del tenant.
    Estados: pending → approved / rejected.
    """
    __tablename__ = "vacation_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending, approved, rejected
    reviewed_by: Mapped[str] = mapped_column(String, nullable=True)  # user_id del revisor
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Extended absence fields
    absence_type: Mapped[str] = mapped_column(String(50), default="vacation", nullable=True)
    document_path: Mapped[str] = mapped_column(String(255), nullable=True)



class Meeting(Base):
    """
    Reunión programada con uno o más participantes.
    """
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=True)
    organizer_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    attendees: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # lista de user_ids
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Task(Base):
    """
    Tarea asignable a un empleado con prioridad y estado.
    """
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)  # low, medium, high, urgent
    status: Mapped[str] = mapped_column(String(20), default="todo", nullable=False)  # todo, in_progress, done
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
