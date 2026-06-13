from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class DashboardWidgetBase(BaseModel):
    title: str
    widget_type: str
    data_source: str
    config: Optional[Dict[str, Any]] = None
    layout_x: Optional[int] = 0
    layout_y: Optional[int] = 0
    layout_w: Optional[int] = 1
    layout_h: Optional[int] = 1

class DashboardWidgetCreate(DashboardWidgetBase):
    dashboard_id: str

class DashboardWidgetUpdate(BaseModel):
    title: Optional[str] = None
    widget_type: Optional[str] = None
    data_source: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    layout_x: Optional[int] = None
    layout_y: Optional[int] = None
    layout_w: Optional[int] = None
    layout_h: Optional[int] = None

class DashboardWidgetResponse(DashboardWidgetBase):
    id: str
    dashboard_id: str

    class Config:
        from_attributes = True

class DashboardBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: Optional[bool] = False

class DashboardCreate(DashboardBase):
    owner_id: Optional[str] = None

class DashboardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None

class DashboardResponse(DashboardBase):
    id: str
    owner_id: Optional[str] = None
    created_at: datetime
    widgets: List[DashboardWidgetResponse] = []

    class Config:
        from_attributes = True
