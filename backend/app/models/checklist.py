from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Integer, Text
from datetime import datetime, timezone
import uuid
from app.models.base import Base
from typing import List, Optional


class ChecklistTemplate(Base):
    __tablename__ = "checklist_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="onboarding", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    template_tasks: Mapped[List["ChecklistTemplateTask"]] = relationship(back_populates="template", cascade="all, delete-orphan")


class ChecklistTemplateTask(Base):
    __tablename__ = "checklist_template_tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    template_id: Mapped[str] = mapped_column(String, ForeignKey("checklist_templates.id", ondelete="CASCADE"), nullable=False)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    responsible_role: Mapped[str] = mapped_column(String(50), default="employee")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    template: Mapped["ChecklistTemplate"] = relationship(back_populates="template_tasks")


class ActiveChecklist(Base):
    __tablename__ = "active_checklists"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    template_id: Mapped[str] = mapped_column(String, ForeignKey("checklist_templates.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    progress: Mapped[float] = mapped_column(default=0.0)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tasks: Mapped[List["ChecklistTask"]] = relationship(back_populates="checklist", cascade="all, delete-orphan")


class ChecklistTask(Base):
    __tablename__ = "checklist_tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    checklist_id: Mapped[str] = mapped_column(String, ForeignKey("active_checklists.id", ondelete="CASCADE"), nullable=False)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    responsible_role: Mapped[str] = mapped_column(String(50), default="employee")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    checklist: Mapped["ActiveChecklist"] = relationship(back_populates="tasks")
