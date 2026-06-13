from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class PageMetadataBase(BaseModel):
    module_name: str = Field(..., max_length=50)
    page_name: str = Field(..., max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    schema_data: Dict[str, Any] = Field(default_factory=dict)

class PageMetadataCreate(PageMetadataBase):
    pass

class PageMetadataUpdate(BaseModel):
    description: Optional[str] = Field(None, max_length=255)
    schema_data: Optional[Dict[str, Any]] = None

class PageMetadataResponse(PageMetadataBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }
