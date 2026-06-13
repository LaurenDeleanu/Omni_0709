from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Numeric, Text, ForeignKey, Date, Integer, Float
from datetime import datetime, timezone, date
import uuid
from typing import List, Optional
from app.models.base import Base


class ExpenseClaim(Base):
    """
    Nota de gastos enviada por un empleado para aprobación y reembolso.
    Soporta extracción mediante IA / OCR.
    """
    __tablename__ = "expense_claims"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    merchant: Mapped[str] = mapped_column(String(150), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=True)  # Impuestos / IVA
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)  # pending, approved, rejected, paid
    category: Mapped[str] = mapped_column(String(50), default="other", nullable=False)  # travel, meals, mileage, software, supplies
    receipt_url: Mapped[str] = mapped_column(String(500), nullable=True)  # Enlace al archivo adjunto/imagen
    approved_by_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    comments: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class TimeLog(Base):
    """
    Registro horario avanzado con geolocalización e IP para control de fichajes (US 6.0 / Contabilidad).
    """
    __tablename__ = "time_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    clock_in: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    clock_out: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    geolocation_in: Mapped[str] = mapped_column(String(100), nullable=True)  # "latitude,longitude"
    geolocation_out: Mapped[str] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    device_info: Mapped[str] = mapped_column(String(250), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)


class BreakLog(Base):
    """
    Registro de pausas y descansos durante la jornada laboral.
    """
    __tablename__ = "break_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    time_log_id: Mapped[str] = mapped_column(String, ForeignKey("time_logs.id", ondelete="CASCADE"), nullable=False, index=True)
    break_type: Mapped[str] = mapped_column(String(50), default="coffee", nullable=False)  # coffee, lunch, medical, personal
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)


class WorkSchedule(Base):
    """
    Horario de trabajo planificado para un empleado.
    Define las horas de inicio/fin y los días laborales.
    """
    __tablename__ = "work_schedules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week: Mapped[int] = mapped_column(nullable=False)  # 0 = Lunes, 6 = Domingo
    start_time: Mapped[str] = mapped_column(String(5), nullable=False, default="09:00")  # HH:MM
    end_time: Mapped[str] = mapped_column(String(5), nullable=False, default="18:00")    # HH:MM
    flexible: Mapped[bool] = mapped_column(default=False)


class GeneralShift(Base):
    """
    Plantillas de turnos de trabajo generales creadas por HR.
    """
    __tablename__ = "general_shifts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "Mañana", "Tarde", "Oficina"
    start_time: Mapped[str] = mapped_column(String(5), nullable=False, default="09:00")  # HH:MM
    end_time: Mapped[str] = mapped_column(String(5), nullable=False, default="18:00")    # HH:MM


class JournalEntry(Base):
    """
    Asiento Contable para el Libro Diario (General Ledger) de SAP FI.
    Agrupa varias líneas de débito y crédito.
    """
    __tablename__ = "journal_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    reference: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)  # e.g., EXP-GastoID, PAY-CycleID
    date: Mapped[date] = mapped_column(Date, nullable=False, default=lambda: date.today())
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    lines: Mapped[List["JournalLine"]] = relationship("JournalLine", back_populates="entry", cascade="all, delete-orphan")


class JournalLine(Base):
    """
    Línea individual de un asiento contable.
    """
    __tablename__ = "journal_lines"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    entry_id: Mapped[str] = mapped_column(String, ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    account_code: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., 629000, 410000, 465000
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    debit: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    credit: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)

    entry: Mapped["JournalEntry"] = relationship("JournalEntry", back_populates="lines")


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    spent_amount: Mapped[float] = mapped_column(Float, default=0.0)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    tenant_id: Mapped[str] = mapped_column(String(50), default="default")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lines: Mapped[List["BudgetLine"]] = relationship("BudgetLine", back_populates="budget", cascade="all, delete-orphan")


class BudgetLine(Base):
    __tablename__ = "budget_lines"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    budget_id: Mapped[str] = mapped_column(String, ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    planned_amount: Mapped[float] = mapped_column(Float, default=0.0)
    actual_amount: Mapped[float] = mapped_column(Float, default=0.0)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    budget: Mapped["Budget"] = relationship("Budget", back_populates="lines")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    type: Mapped[str] = mapped_column(String(10), default="payable")  # payable or receivable
    vendor_client: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")  # ISO 4217
    exchange_rate: Mapped[float] = mapped_column(Float, default=1.0)  # To base currency (EUR)
    base_amount: Mapped[float] = mapped_column(Float, default=0.0)  # Amount in EUR
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft/sent/paid/overdue/cancelled
    issue_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    paid_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(50), default="default")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CurrencyRate(Base):
    __tablename__ = "currency_rates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    code: Mapped[str] = mapped_column(String(3), nullable=False)  # USD, GBP, MXN
    rate_to_eur: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

