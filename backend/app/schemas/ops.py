from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class FacilityAssetBase(BaseModel):
    name: str
    type: str
    location: Optional[str] = None
    status: Optional[str] = "available"

class FacilityAssetCreate(FacilityAssetBase):
    pass

class FacilityAssetResponse(FacilityAssetBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True

class AssetBookingBase(BaseModel):
    asset_id: str
    employee_id: str
    start_time: datetime
    end_time: datetime
    status: Optional[str] = "confirmed"

class AssetBookingCreate(AssetBookingBase):
    pass

class AssetBookingResponse(AssetBookingBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True

class VisitorLogBase(BaseModel):
    visitor_name: str
    company: Optional[str] = None
    host_id: str
    expected_arrival: datetime
    status: Optional[str] = "expected"

class VisitorLogCreate(VisitorLogBase):
    pass

class VisitorLogUpdate(BaseModel):
    status: Optional[str] = None
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None

class VisitorLogResponse(VisitorLogBase):
    id: str
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class CalendarBookingResponse(BaseModel):
    id: str
    asset_id: str
    asset_name: Optional[str] = None
    asset_type: Optional[str] = None
    employee_name: Optional[str] = None
    start_time: datetime
    end_time: datetime
    status: str

    class Config:
        from_attributes = True

class MaintenanceRequestBase(BaseModel):
    asset_id: Optional[str] = None
    title: str
    description: Optional[str] = ""
    priority: Optional[str] = "medium"
    status: Optional[str] = "reported"
    reported_by_id: str

class MaintenanceRequestCreate(MaintenanceRequestBase):
    pass

class MaintenanceRequestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_to_id: Optional[str] = None
    resolution_notes: Optional[str] = None

class MaintenanceRequestResponse(MaintenanceRequestBase):
    id: str
    assigned_to_id: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class MaintenanceStats(BaseModel):
    total: int
    reported: int
    in_progress: int
    resolved: int
    closed: int
    low: int
    medium: int
    high: int
    critical: int
