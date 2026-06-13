from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Boolean, Text, ForeignKey
from datetime import datetime, timezone
import uuid
from app.models.base import Base


class Notification(Base):
    """
    Notificaciones in-app para usuarios del tenant.
    """
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)  # vacation, payroll, task, kudos, system
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
