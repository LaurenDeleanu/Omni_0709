from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, ForeignKey, JSON
from datetime import datetime, timezone
import uuid
from app.models.base import Base


class WorkflowTemplate(Base):
    """
    Plantillas de workflow de Onboarding u Offboarding.
    """
    __tablename__ = "workflow_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # onboarding, offboarding
    steps: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # List of dict steps


class UserWorkflow(Base):
    """
    Seguimiento de un workflow (checklist) activo para un empleado.
    """
    __tablename__ = "user_workflows"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id: Mapped[str] = mapped_column(String, ForeignKey("workflow_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="in_progress", nullable=False)  # in_progress, completed
    steps_status: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # dict mapping step ID to completion details
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
