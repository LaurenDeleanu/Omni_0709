from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Numeric, Text, ForeignKey, Date, JSON, func
from datetime import datetime, timezone, date
import uuid
from app.models.base import Base


class ITAsset(Base):
    """
    Representa un activo físico de hardware asignado a un empleado o disponible.
    """
    __tablename__ = "it_assets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), default="laptop", nullable=False)  # laptop, monitor, mobile, etc.
    status: Mapped[str] = mapped_column(String(30), default="available", nullable=False)  # available, assigned, repair, retired
    assigned_to_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=True)
    cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ITTicket(Base):
    """
    Ticket de soporte técnico generado internamente por empleados.
    """
    __tablename__ = "it_tickets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="hardware", nullable=False)  # hardware, software, accounts, network
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)  # low, medium, high, critical
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)  # open, in_progress, resolved, closed
    requester_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assignee_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    solved_by: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolution_notes: Mapped[str] = mapped_column(Text, nullable=True)
    ticket_meta: Mapped[dict] = mapped_column("ticket_meta", JSON, default=dict, nullable=False)


class SaaSLicense(Base):
    """
    Control de software SaaS provisionado a los empleados.
    """
    __tablename__ = "saas_licenses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    software_name: Mapped[str] = mapped_column(String(100), nullable=False)  # Slack, Google Workspace, GitHub
    seat_cost: Mapped[float] = mapped_column(Numeric(8, 2), default=0.0, nullable=False)
    assigned_to_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, suspended, expired
    renewal_date: Mapped[date] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ITRequisition(Base):
    """
    Solicitud de aprovisionamiento de hardware o licencias de software (SAP MM / ITSM).
    """
    __tablename__ = "it_requisitions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(50), nullable=False)  # hardware, software
    item_name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., MacBook Pro, GitHub Enterprise
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending, approved, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ITKnowledgeArticle(Base):
    __tablename__ = "it_kb_articles"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    title: Mapped[str] = mapped_column(String, nullable=False)
    problem_description: Mapped[str] = mapped_column(Text, nullable=False)
    symptoms: Mapped[dict] = mapped_column(JSON, nullable=True)
    root_cause: Mapped[str] = mapped_column(Text, nullable=True)
    resolution_steps: Mapped[dict] = mapped_column(JSON, nullable=True)
    prevention_tips: Mapped[dict] = mapped_column(JSON, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=True)
    tags: Mapped[dict] = mapped_column(JSON, nullable=True)
    source_ticket_id: Mapped[str] = mapped_column(String, nullable=True)
    author: Mapped[str] = mapped_column(String, nullable=True)
    view_count: Mapped[int] = mapped_column(default=0)
    helpful_count: Mapped[int] = mapped_column(default=0)
    embedding_id: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

