from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime, date


class HistoryCreate(BaseModel):
    position: str
    department: Optional[str] = None
    salary: Optional[float] = None
    currency: str = "EUR"
    start_date: date
    end_date: Optional[date] = None
    notes: Optional[str] = None


class HistoryUpdate(BaseModel):
    position: Optional[str] = None
    department: Optional[str] = None
    salary: Optional[float] = None
    currency: Optional[str] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None


class HistoryResponse(HistoryCreate):
    id: str
    user_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
