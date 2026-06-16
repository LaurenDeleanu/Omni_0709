from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Text
from datetime import datetime, timezone
import uuid
from app.models.base import Base


class VisualWorkflow(Base):
    __tablename__ = "visual_workflows"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Allows a workflow to optionally be tied directly to a specific agent as its default "bot"
    # But it's not strictly required, as workflows can be standalone
    agent_id: Mapped[str] = mapped_column(String, nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
