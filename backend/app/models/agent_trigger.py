from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, JSON, Boolean
from datetime import datetime, timezone
import uuid
from app.models.base import Base

class Trigger(Base):
    """
    Representa un disparador (trigger) que activa la ejecución de un Agente o un Workflow.
    """
    __tablename__ = "agent_triggers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    type: Mapped[str] = mapped_column(String(50), nullable=False) # webhook, cron, event, manual
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False) # Config: cron expressions, headers, secret keys, etc.
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    agent = relationship("Agent", back_populates="triggers")
