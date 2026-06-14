"""
TaxBracket model — Configurable tax brackets, rates, and thresholds per country.
Stored in the global database (not tenant-scoped) for shared tax configuration.
"""
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, Boolean, JSON, Integer, DateTime
from datetime import datetime, timezone
from app.models.base import GlobalBase


class TaxBracket(GlobalBase):
    __tablename__ = "tax_brackets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    country_code: Mapped[str] = mapped_column(String(2), index=True, nullable=False)  # ES, US, GB, etc.
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="")
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    tax_year: Mapped[int] = mapped_column(Integer, default=2026)

    # Income tax brackets — JSON array: [[min, max, rate], ...]
    brackets: Mapped[list] = mapped_column(JSON, default=list)

    # Social security / FICA contributions
    social_security_employee: Mapped[float] = mapped_column(Float, default=0)
    social_security_employer: Mapped[float] = mapped_column(Float, default=0)

    # Deductions and allowances
    standard_deduction: Mapped[float] = mapped_column(Float, default=0)
    personal_allowance: Mapped[float] = mapped_column(Float, default=0)

    # VAT / Sales Tax
    vat_rate: Mapped[float] = mapped_column(Float, default=0)
    vat_reduced_rate: Mapped[float] = mapped_column(Float, default=0)
    vat_food_rate: Mapped[float] = mapped_column(Float, default=0)

    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)  # True if modified by admin
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual")  # "manual", "eu_vat_api", "hmrc_api", etc.

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
