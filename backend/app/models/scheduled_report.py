from typing import Optional
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import GlobalBase
from datetime import datetime, timezone

class ScheduledReport(GlobalBase):
    __tablename__ = "scheduled_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True) # None para todos o específico
    name: Mapped[str] = mapped_column(String, nullable=False, default="Scheduled Report")
    email_to: Mapped[str] = mapped_column(String, nullable=False)
    frequency: Mapped[str] = mapped_column(String, nullable=False) # 'daily', 'weekly', 'monthly'
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
