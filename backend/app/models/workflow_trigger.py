from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Boolean, Text, ForeignKey
from datetime import datetime, timezone
import uuid
from app.models.base import Base


class WorkflowTrigger(Base):
    __tablename__ = "workflow_triggers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    bot_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="MANUAL", nullable=False)
    config: Mapped[str] = mapped_column(Text, default="{}")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
