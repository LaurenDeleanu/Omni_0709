from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date


# ==========================================
# IT ASSETS SCHEMAS
# ==========================================
class ITAssetBase(BaseModel):
    name: str
    serial_number: str
    category: str = "laptop"
    status: str = "available"
    assigned_to_id: Optional[str] = None
    purchase_date: Optional[date] = None
    cost: Optional[float] = None


class ITAssetCreate(ITAssetBase):
    pass


class ITAssetUpdate(BaseModel):
    name: Optional[str] = None
    serial_number: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    assigned_to_id: Optional[str] = None
    purchase_date: Optional[date] = None
    cost: Optional[float] = None


class ITAssetResponse(ITAssetBase):
    id: str
    created_at: datetime
    accumulated_depreciation: Optional[float] = None
    net_book_value: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# IT TICKETS SCHEMAS
# ==========================================
class ITTicketBase(BaseModel):
    title: str
    description: str
    category: str = "hardware"
    priority: str = "medium"
    status: str = "open"
    requester_id: str
    assignee_id: Optional[str] = None


class ITTicketCreate(BaseModel):
    title: str
    description: str
    category: str = "hardware"
    priority: str = "medium"
    requester_id: str


class ITTicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    resolution_notes: Optional[str] = None
    solved_by: Optional[str] = None


class ITTicketResponse(ITTicketBase):
    id: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    solved_by: Optional[str] = None
    resolution_notes: Optional[str] = None
    ticket_meta: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# SAAS LICENSES SCHEMAS
# ==========================================
class SaaSLicenseBase(BaseModel):
    software_name: str
    seat_cost: float = 0.0
    assigned_to_id: Optional[str] = None
    status: str = "active"
    renewal_date: Optional[date] = None


class SaaSLicenseCreate(SaaSLicenseBase):
    pass


class SaaSLicenseUpdate(BaseModel):
    software_name: Optional[str] = None
    seat_cost: Optional[float] = None
    assigned_to_id: Optional[str] = None
    status: Optional[str] = None
    renewal_date: Optional[date] = None


class SaaSLicenseResponse(SaaSLicenseBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# IT REQUISITION SCHEMAS
# ==========================================
class ITRequisitionBase(BaseModel):
    user_id: str
    item_type: str  # hardware, software
    item_name: str
    reason: Optional[str] = None
    status: str = "pending"


class ITRequisitionCreate(BaseModel):
    item_type: str
    item_name: str
    reason: Optional[str] = None


class ITRequisitionUpdate(BaseModel):
    status: str


class ITRequisitionResponse(ITRequisitionBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# IT KNOWLEDGE BASE SCHEMAS
# ==========================================
class ITKnowledgeArticleResponse(BaseModel):
    id: str
    title: str
    problem_description: str
    symptoms: Optional[list] = None
    root_cause: Optional[str] = None
    resolution_steps: Optional[list] = None
    prevention_tips: Optional[list] = None
    category: Optional[str] = None
    tags: Optional[list] = None
    source_ticket_id: Optional[str] = None
    author: Optional[str] = None
    view_count: int = 0
    helpful_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KBListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[ITKnowledgeArticleResponse]

