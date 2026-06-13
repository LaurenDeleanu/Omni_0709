from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, ForeignKey, Text, Boolean
from datetime import datetime, timezone
import uuid
from app.models.base import Base


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    parent_id: Mapped[str] = mapped_column(String, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True)
    author_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
