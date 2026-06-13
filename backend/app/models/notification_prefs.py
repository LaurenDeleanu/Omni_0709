from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Boolean
from datetime import datetime, timezone
import uuid
from app.models.base import Base


class NotificationPrefs(Base):
    __tablename__ = "notification_prefs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    push_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    in_app_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    digest_frequency: Mapped[str] = mapped_column(String(20), default="daily")
    muted_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
