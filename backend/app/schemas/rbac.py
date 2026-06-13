from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class PermissionResponse(BaseModel):
    id: str
    module: str
    action: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class RolePermissionResponse(BaseModel):
    id: str
    role_id: str
    permission_id: str
    permission: PermissionResponse

    class Config:
        from_attributes = True

class RoleBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=255)

class RoleCreate(RoleBase):
    permission_ids: List[str] = []

class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    permission_ids: Optional[List[str]] = None

class RoleResponse(RoleBase):
    id: str
    is_system_default: bool
    created_at: datetime
    permissions: List[RolePermissionResponse] = []

    class Config:
        from_attributes = True
