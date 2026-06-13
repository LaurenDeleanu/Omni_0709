from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Boolean, JSON
from datetime import datetime, timezone
import uuid
from app.models.base import GlobalBase

class Tenant(GlobalBase):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    schema_name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    logo_url: Mapped[str] = mapped_column(String(255), nullable=True)
    primary_color: Mapped[str] = mapped_column(String(50), nullable=True)
    enabled_modules: Mapped[dict] = mapped_column(JSON, default=lambda: {
        "it": True, "finance": True, "training": True, "schedules": True
    }, nullable=True)
    
    # BYOK credentials
    custom_openai_key: Mapped[str] = mapped_column(String(500), nullable=True)
    custom_gemini_key: Mapped[str] = mapped_column(String(500), nullable=True)
    custom_openrouter_key: Mapped[str] = mapped_column(String(500), nullable=True)
    custom_anthropic_key: Mapped[str] = mapped_column(String(500), nullable=True)
    custom_grok_key: Mapped[str] = mapped_column(String(500), nullable=True)
    custom_groq_key: Mapped[str] = mapped_column(String(500), nullable=True)
    
    tier: Mapped[str] = mapped_column(String(50), default="FREE", nullable=False)
    data_residency: Mapped[str] = mapped_column(String(10), default="EU", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
