from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import Column, String, DateTime, JSON, Boolean, Text
from app.models.base import Base

class Approval(Base):
    __tablename__ = "approvals"

    id = Column(String(50), primary_key=True, index=True)
    tenant_id = Column(String(50), index=True, default="default")
    
    workflow_id = Column(String(50), index=True, nullable=True)
    agent_id = Column(String(50), index=True, nullable=True)
    run_id = Column(String(50), index=True, nullable=True)
    
    requested_by = Column(String(50), nullable=True) # E.g., 'system' or 'agent-xyz'
    status = Column(String(20), default="PENDING", index=True) # PENDING, APPROVED, REJECTED, TIMEOUT
    approved_by = Column(String(50), nullable=True) # User ID who resolved it
    
    context_data = Column(JSON, default={}) # Payload data to display to user
    resolution_notes = Column(Text, nullable=True) # Optional note from approver
    
    timeout_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "workflow_id": self.workflow_id,
            "agent_id": self.agent_id,
            "run_id": self.run_id,
            "requested_by": self.requested_by,
            "status": self.status,
            "approved_by": self.approved_by,
            "context_data": self.context_data,
            "resolution_notes": self.resolution_notes,
            "timeout_at": self.timeout_at.isoformat() if self.timeout_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
