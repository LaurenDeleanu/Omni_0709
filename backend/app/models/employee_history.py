from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, JSON, Text
from datetime import datetime, timezone
import uuid
from app.models.base import Base


class EmployeeHistory(Base):
    __tablename__ = "employee_history"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    employee_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(200), nullable=False)
    old_value: Mapped[str] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=True)
    changed_by: Mapped[str] = mapped_column(String, nullable=True)
    changed_by_name: Mapped[str] = mapped_column(String(200), nullable=True)
    change_reason: Mapped[str] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
