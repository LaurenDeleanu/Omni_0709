from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Text, ForeignKey
from datetime import datetime, timezone
import uuid
from app.models.base import Base

class AuditLog(Base):
    """
    Registro persistente de auditoría para auditorías de seguridad y acciones administrativas.
    Se guarda dentro del esquema del inquilino (tenant).
    """
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. "MODULE_TOGGLE", "COURSE_ASSIGNED", "ROLE_CHANGED", "TASK_ASSIGNED"
    details: Mapped[str] = mapped_column(Text, nullable=True) # JSON or plain text description
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
