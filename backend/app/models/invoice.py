from sqlalchemy import Column, String, Float, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone, date
import uuid
from typing import Optional
from app.models.base import Base


class CustomerInvoice(Base):
    __tablename__ = "customer_invoices"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tax_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    line_items: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    date: Mapped[Optional[date]] = mapped_column(DateTime, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payment_terms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
