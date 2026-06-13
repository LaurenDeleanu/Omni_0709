from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Text, Boolean
from datetime import datetime, timezone
import uuid
from app.models.base import Base


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
