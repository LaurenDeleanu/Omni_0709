from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Boolean, Text, JSON
from datetime import datetime, timezone
import uuid
from app.models.base import Base


class OAuthClient(Base):
    __tablename__ = "oauth_clients"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    client_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    client_secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    redirect_uris: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_scopes: Mapped[str] = mapped_column(String(500), default="read:all", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_by: Mapped[str] = mapped_column(String, nullable=True)


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    client_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    access_token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    scopes: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
