from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date


# ==========================================
# EXPENSE CLAIMS SCHEMAS
# ==========================================
class ExpenseClaimBase(BaseModel):
    user_id: str
    merchant: str
    date: date
    total_amount: float
    tax_amount: Optional[float] = 0.0
    status: str = "pending"
    category: str = "other"
    receipt_url: Optional[str] = None
    approved_by_id: Optional[str] = None
    comments: Optional[str] = None


class ExpenseClaimCreate(BaseModel):
    user_id: str
    merchant: str
    date: date
    total_amount: float
    tax_amount: Optional[float] = 0.0
    category: str = "other"
    receipt_url: Optional[str] = None
    comments: Optional[str] = None


class ExpenseClaimUpdate(BaseModel):
    merchant: Optional[str] = None
    date: Optional[date] = None
    total_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    status: Optional[str] = None
    category: Optional[str] = None
    receipt_url: Optional[str] = None
    approved_by_id: Optional[str] = None
    comments: Optional[str] = None


class ExpenseClaimResponse(ExpenseClaimBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# TIME LOG SCHEMAS (FICHAJE AVANZADO)
# ==========================================
class TimeLogBase(BaseModel):
    user_id: str
    clock_in: datetime
    clock_out: Optional[datetime] = None
    geolocation_in: Optional[str] = None
    geolocation_out: Optional[str] = None
    ip_address: Optional[str] = None
    device_info: Optional[str] = None
    notes: Optional[str] = None


class TimeLogClockIn(BaseModel):
    user_id: str
    geolocation_in: Optional[str] = None
    ip_address: Optional[str] = None
    device_info: Optional[str] = None
    notes: Optional[str] = None


class TimeLogClockOut(BaseModel):
    geolocation_out: Optional[str] = None
    notes: Optional[str] = None


class TimeLogResponse(TimeLogBase):
    id: str

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# BREAK LOG SCHEMAS (PAUSAS DE TRABAJO)
# ==========================================
class BreakLogBase(BaseModel):
    break_type: str = "coffee"  # coffee, lunch, medical, personal
    notes: Optional[str] = None


class BreakLogCreate(BreakLogBase):
    pass


class BreakLogResponse(BreakLogBase):
    id: str
    time_log_id: str
    start_time: datetime
    end_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Extended TimeLogResponse to include break logs
class TimeLogResponseWithBreaks(TimeLogResponse):
    breaks: List[BreakLogResponse] = []


# ==========================================
# WORK SCHEDULE SCHEMAS (HORARIOS DE TRABAJO)
# ==========================================
class WorkScheduleCreate(BaseModel):
    day_of_week: int  # 0-6
    start_time: str = "09:00"
    end_time: str = "18:00"
    flexible: bool = False


class WorkScheduleResponse(BaseModel):
    id: str
    user_id: str
    day_of_week: int
    start_time: str
    end_time: str
    flexible: bool

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# GENERAL SHIFT SCHEMAS (TURNOS GENERALES)
# ==========================================
class GeneralShiftBase(BaseModel):
    name: str
    start_time: str = "09:00"
    end_time: str = "18:00"


class GeneralShiftCreate(GeneralShiftBase):
    pass


class GeneralShiftResponse(GeneralShiftBase):
    id: str

    model_config = ConfigDict(from_attributes=True)


class BulkShiftAssignment(BaseModel):
    employee_ids: List[str]
    general_shift_id: str
    days: List[int]


# ==========================================
# GENERAL LEDGER SCHEMAS (SAP FI)
# ==========================================
class JournalLineResponse(BaseModel):
    id: str
    entry_id: str
    account_code: str
    account_name: str
    debit: float
    credit: float

    model_config = ConfigDict(from_attributes=True)


class JournalEntryResponse(BaseModel):
    id: str
    reference: str
    date: date
    description: str
    created_at: datetime
    lines: List[JournalLineResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# BUDGET SCHEMAS
# ==========================================
class BudgetLineBase(BaseModel):
    description: str
    planned_amount: float = 0.0
    actual_amount: float = 0.0
    category: Optional[str] = None


class BudgetLineCreate(BudgetLineBase):
    pass


class BudgetLineUpdate(BaseModel):
    description: Optional[str] = None
    planned_amount: Optional[float] = None
    actual_amount: Optional[float] = None
    category: Optional[str] = None


class BudgetLineResponse(BudgetLineBase):
    id: str
    budget_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetBase(BaseModel):
    name: str
    department: Optional[str] = None
    fiscal_year: int
    total_amount: float = 0.0
    spent_amount: float = 0.0
    category: Optional[str] = None
    status: str = "active"


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    fiscal_year: Optional[int] = None
    total_amount: Optional[float] = None
    spent_amount: Optional[float] = None
    category: Optional[str] = None
    status: Optional[str] = None


class BudgetResponse(BudgetBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    lines: List[BudgetLineResponse] = []
    variance: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class BudgetSummaryResponse(BaseModel):
    total_budgeted: float = 0.0
    total_spent: float = 0.0
    total_remaining: float = 0.0
    budget_count: int = 0
    by_department: dict = {}
    budgets: List[BudgetResponse] = []


# ==========================================
# INVOICE SCHEMAS
# ==========================================
class InvoiceCreate(BaseModel):
    type: str = "payable"  # payable or receivable
    vendor_client: str = ""
    description: str = ""
    amount: float = 0.0
    tax_amount: float = 0.0
    currency: str = "EUR"
    exchange_rate: float = 1.0
    status: str = "draft"
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    category: Optional[str] = None


class InvoiceUpdate(BaseModel):
    type: Optional[str] = None
    vendor_client: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    tax_amount: Optional[float] = None
    currency: Optional[str] = None
    exchange_rate: Optional[float] = None
    status: Optional[str] = None
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    paid_date: Optional[datetime] = None
    category: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    type: str
    vendor_client: str
    description: str
    amount: float
    tax_amount: float
    total_amount: float
    currency: str
    exchange_rate: float
    base_amount: float
    status: str
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    paid_date: Optional[datetime] = None
    category: Optional[str] = None
    tenant_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceAgingResponse(BaseModel):
    bucket_0_30: float = 0.0
    bucket_31_60: float = 0.0
    bucket_61_90: float = 0.0
    bucket_90_plus: float = 0.0
    total_outstanding: float = 0.0
    count_0_30: int = 0
    count_31_60: int = 0
    count_61_90: int = 0
    count_90_plus: int = 0


# ==========================================
# CURRENCY SCHEMAS
# ==========================================
class CurrencyRateResponse(BaseModel):
    id: str
    code: str
    rate_to_eur: float
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CurrencyConvertRequest(BaseModel):
    from_currency: str
    to_currency: str
    amount: float


class CurrencyConvertResponse(BaseModel):
    from_currency: str
    to_currency: str
    original_amount: float
    converted_amount: float
    rate: float

