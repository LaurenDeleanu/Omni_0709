from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, JSON
from datetime import datetime, timezone
import uuid
from app.models.base import Base


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    workflow_id: Mapped[str] = mapped_column(String, ForeignKey("visual_workflows.id", ondelete="CASCADE"), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # DAG pathing configurations
    next_nodes: Mapped[list] = mapped_column(JSON, default=list) # List of node IDs
    condition: Mapped[str] = mapped_column(Text, nullable=True)  # Optional expression to route
    
    # Legacy linear order (kept for backwards compatibility during migration)
    order: Mapped[int] = mapped_column(Integer, default=0)
    
    config: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
