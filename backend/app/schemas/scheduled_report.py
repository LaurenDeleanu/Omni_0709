from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class ScheduleCreate(BaseModel):
    email_to: EmailStr
    frequency: str  # 'daily', 'weekly', 'monthly'
    is_active: bool = True

class ScheduleResponse(BaseModel):
    id: str
    tenant_id: Optional[str]
    email_to: EmailStr
    frequency: str
    is_active: bool
    last_run_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
