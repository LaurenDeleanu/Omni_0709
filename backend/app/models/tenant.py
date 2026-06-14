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

    # BYOK credentials — encrypted at rest
    _custom_openai_key: Mapped[str] = mapped_column("custom_openai_key", String(500), nullable=True)
    _custom_gemini_key: Mapped[str] = mapped_column("custom_gemini_key", String(500), nullable=True)
    _custom_openrouter_key: Mapped[str] = mapped_column("custom_openrouter_key", String(500), nullable=True)
    _custom_anthropic_key: Mapped[str] = mapped_column("custom_anthropic_key", String(500), nullable=True)
    _custom_grok_key: Mapped[str] = mapped_column("custom_grok_key", String(500), nullable=True)
    _custom_groq_key: Mapped[str] = mapped_column("custom_groq_key", String(500), nullable=True)

    tier: Mapped[str] = mapped_column(String(50), default="FREE", nullable=False)
    stripe_customer_id: Mapped[str] = mapped_column(String(100), nullable=True)
    subscription_id: Mapped[str] = mapped_column(String(100), nullable=True)
    subscription_status: Mapped[str] = mapped_column(String(50), nullable=True, default="inactive")
    subscription_tier: Mapped[str] = mapped_column(String(50), nullable=True)
    data_residency: Mapped[str] = mapped_column(String(10), default="EU", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    @staticmethod
    def _encrypt(value: str) -> str:
        if not value:
            return None
        from app.services.field_encryption import encrypt_field
        return encrypt_field(value)

    @staticmethod
    def _decrypt(value: str) -> str:
        if not value:
            return ""
        try:
            from app.services.field_encryption import decrypt_field
            return decrypt_field(value)
        except Exception:
            return value  # plaintext fallback for existing unencrypted data

    @property
    def custom_openai_key(self) -> str:
        return self._decrypt(self._custom_openai_key)

    @custom_openai_key.setter
    def custom_openai_key(self, value: str):
        self._custom_openai_key = self._encrypt(value)

    @property
    def custom_gemini_key(self) -> str:
        return self._decrypt(self._custom_gemini_key)

    @custom_gemini_key.setter
    def custom_gemini_key(self, value: str):
        self._custom_gemini_key = self._encrypt(value)

    @property
    def custom_openrouter_key(self) -> str:
        return self._decrypt(self._custom_openrouter_key)

    @custom_openrouter_key.setter
    def custom_openrouter_key(self, value: str):
        self._custom_openrouter_key = self._encrypt(value)

    @property
    def custom_anthropic_key(self) -> str:
        return self._decrypt(self._custom_anthropic_key)

    @custom_anthropic_key.setter
    def custom_anthropic_key(self, value: str):
        self._custom_anthropic_key = self._encrypt(value)

    @property
    def custom_grok_key(self) -> str:
        return self._decrypt(self._custom_grok_key)

    @custom_grok_key.setter
    def custom_grok_key(self, value: str):
        self._custom_grok_key = self._encrypt(value)

    @property
    def custom_groq_key(self) -> str:
        return self._decrypt(self._custom_groq_key)

    @custom_groq_key.setter
    def custom_groq_key(self, value: str):
        self._custom_groq_key = self._encrypt(value)
