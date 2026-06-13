from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Text, ForeignKey
from datetime import datetime, timezone
import uuid
from app.models.base import Base


class Kudos(Base):
    """
    Kudos de agradecimiento entre compañeros.
    """
    __tablename__ = "kudos"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    sender_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    receiver_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    badge: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. Team Player, Above & Beyond, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
