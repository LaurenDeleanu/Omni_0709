from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Integer, Text, ForeignKey
from datetime import datetime, timezone
import uuid
from app.models.base import Base


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    bot_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)
    config: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
