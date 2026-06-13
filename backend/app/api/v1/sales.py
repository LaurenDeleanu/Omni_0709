from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.api.dependencies import get_tenant_db, require_super_admin
from app.models.sales import Client, Lead

router = APIRouter()

# --- Schemas ---

class ClientCreate(BaseModel):
    company_name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    primary_contact_phone: Optional[str] = None

class ClientResponse(ClientCreate):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class LeadCreate(BaseModel):
    title: str
    contact_name: Optional[str] = None
    company_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    estimated_value: Optional[float] = 0.0
    probability: Optional[int] = 10
    stage: Optional[str] = "inbound"

class LeadResponse(LeadCreate):
    id: str
    client_id: Optional[str] = None
    expected_close_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class StageUpdate(BaseModel):
    stage: str

# --- Endpoints ---

@router.get("/leads", response_model=List[LeadResponse])
async def get_leads(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Lead).order_by(Lead.created_at.desc()))
    return result.scalars().all()

@router.post("/leads", response_model=LeadResponse)
async def create_lead(data: LeadCreate, db: AsyncSession = Depends(get_tenant_db)):
    db_lead = Lead(**data.model_dump())
    db.add(db_lead)
    await db.commit()
    await db.refresh(db_lead)
    return db_lead

@router.patch("/leads/{lead_id}/stage")
async def update_lead_stage(lead_id: str, payload: StageUpdate, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead.stage = payload.stage
    await db.commit()
    return {"message": "Stage updated successfully"}

@router.get("/clients", response_model=List[ClientResponse])
async def get_clients(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Client).order_by(Client.created_at.desc()))
    return result.scalars().all()

@router.post("/clients", response_model=ClientResponse)
async def create_client(data: ClientCreate, db: AsyncSession = Depends(get_tenant_db)):
    db_client = Client(**data.model_dump())
    db.add(db_client)
    await db.commit()
    await db.refresh(db_client)
    return db_client

class LeadUpdate(BaseModel):
    title: Optional[str] = None
    contact_name: Optional[str] = None
    company_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    estimated_value: Optional[float] = None
    probability: Optional[int] = None
    stage: Optional[str] = None
    client_id: Optional[str] = None

class ClientUpdate(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    primary_contact_name: Optional[str] = None
    primary_contact_email: Optional[str] = None
    primary_contact_phone: Optional[str] = None

@router.put("/leads/{lead_id}", response_model=LeadResponse)
async def update_lead(lead_id: str, data: LeadUpdate, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lead, key, value)
        
    await db.commit()
    await db.refresh(lead)
    return lead

@router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    await db.delete(lead)
    await db.commit()
    return {"message": "Lead deleted successfully"}

@router.put("/clients/{client_id}", response_model=ClientResponse)
async def update_client(client_id: str, data: ClientUpdate, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalars().first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(client, key, value)
        
    await db.commit()
    await db.refresh(client)
    return client

@router.delete("/clients/{client_id}")
async def delete_client(client_id: str, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalars().first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    await db.delete(client)
    await db.commit()
    return {"message": "Client deleted successfully"}
