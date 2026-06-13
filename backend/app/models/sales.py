from sqlalchemy import Column, String, Float, Integer, DateTime, Text, ForeignKey, func, JSON
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base

class Client(Base):
    __tablename__ = "sales_clients"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name = Column(String, nullable=False)
    industry = Column(String, nullable=True)
    website = Column(String, nullable=True)
    primary_contact_name = Column(String, nullable=True)
    primary_contact_email = Column(String, nullable=True)
    primary_contact_phone = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Un Cliente puede tener múltiples Leads (ventas cruzadas o repetidas)
    leads = relationship("Lead", back_populates="client")


class Lead(Base):
    __tablename__ = "sales_leads"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False) # e.g. "Acme Corp Redesign"
    client_id = Column(String, ForeignKey("sales_clients.id"), nullable=True)
    
    # If not yet a client, we store raw contact info
    contact_name = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    
    estimated_value = Column(Float, default=0.0)
    probability = Column(Integer, default=10) # 0 to 100%
    stage = Column(String, nullable=False, default="inbound") # inbound, discovery, proposal, negotiation, won, lost
    
    score = Column(Float, default=0.0)
    score_breakdown = Column(JSON, nullable=True)
    
    expected_close_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    client = relationship("Client", back_populates="leads")
