from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Text, Boolean, Integer, JSON, Float
from datetime import datetime, timezone
import uuid
from app.models.base import Base


class Plugin(Base):
    __tablename__ = "plugins"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    author_email: Mapped[str] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="tools")
    icon: Mapped[str] = mapped_column(String(10), default="🧩")
    manifest: Mapped[dict] = mapped_column(JSON, default=dict)
    source_code_url: Mapped[str] = mapped_column(String(500), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    install_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_rating: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class PluginInstall(Base):
    __tablename__ = "plugin_installs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    plugin_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PluginReview(Base):
    __tablename__ = "plugin_reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    plugin_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    user_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
