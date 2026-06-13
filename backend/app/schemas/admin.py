from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional, List, Dict
from datetime import datetime, date

class AuditLogResponse(BaseModel):
    id: str
    user_id: str
    action: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TenantModulesUpdate(BaseModel):
    enabled_modules: Dict[str, bool]

class CourseAssignmentCreate(BaseModel):
    user_ids: List[str]
    course_id: str

class TaskAssignmentCreate(BaseModel):
    user_ids: List[str]
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    priority: str = "medium" # low, medium, high, urgent

class UserRoleUpdate(BaseModel):
    role: str # employee, hr_admin, it_manager, finance_manager
