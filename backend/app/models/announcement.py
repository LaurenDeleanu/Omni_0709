from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Boolean, Text, ForeignKey
from datetime import datetime, timezone
import uuid
from app.models.base import Base


class Announcement(Base):
    """
    Anuncios globales de la compañía para todos los empleados.
    """
    __tablename__ = "announcements"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
