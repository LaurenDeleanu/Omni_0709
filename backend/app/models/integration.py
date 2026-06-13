from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Text, ForeignKey, UniqueConstraint
from datetime import datetime, timezone
import uuid
from app.models.base import Base

class UserIntegration(Base):
    """
    Guarda los tokens de integración (OAuth) para cada usuario.
    Permite conexiones User-Level a Google Workspace o Microsoft 365.
    """
    __tablename__ = "user_integrations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False) # 'google' o 'microsoft'
    external_email: Mapped[str] = mapped_column(String(255), nullable=True)
    
    # OAuth Tokens
    access_token: Mapped[str] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Sync settings
    sync_enabled: Mapped[bool] = mapped_column(default=True)
    last_sync_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('user_id', 'provider', name='uq_user_provider'),
    )
