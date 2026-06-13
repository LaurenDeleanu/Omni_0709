from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    department: Optional[str] = None
    is_active: bool = True
    role: str = "employee"
    phone_number: Optional[str] = None
    address: Optional[str] = None
    iban: Optional[str] = None
    social_security_number: Optional[str] = None
    emergency_contact: Optional[str] = None
    contract_type: Optional[str] = "Indefinido"
    hire_date: Optional[datetime] = None
    base_salary: Optional[float] = 50000.0
    country: Optional[str] = "ES"
    manager_id: Optional[str] = None


class UserCreate(UserBase):
    password: Optional[str] = None  # Si se provee, se hashea al crear el usuario


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    iban: Optional[str] = None
    social_security_number: Optional[str] = None
    emergency_contact: Optional[str] = None
    contract_type: Optional[str] = None
    hire_date: Optional[datetime] = None
    base_salary: Optional[float] = None
    country: Optional[str] = None
    manager_id: Optional[str] = None


class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdateInput(BaseModel):
    phone_number: Optional[str] = None
    emergency_contact: Optional[str] = None
    address: Optional[str] = None
    iban: Optional[str] = None


class ProfileChangeRequestResponse(BaseModel):
    id: str
    user_id: str
    field_name: str
    old_value: Optional[str] = None
    new_value: str
    status: str
    requested_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProfileChangeRequestReview(BaseModel):
    approved: bool
