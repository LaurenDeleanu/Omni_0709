from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
from datetime import datetime, timezone
import uuid
from app.models.base import Base

class PushSubscription(Base):
    """
    Suscripciones de Web Push para notificaciones en tiempo real del navegador.
    """
    __tablename__ = "push_subscriptions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    keys: Mapped[dict] = mapped_column(JSON, nullable=False) # Contiene p256dh y auth
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
