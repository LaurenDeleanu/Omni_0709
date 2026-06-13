from sqlalchemy import Column, String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.models.base import Base

class FacilityAsset(Base):
    __tablename__ = "ops_assets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False) # e.g. "Desk 42", "Parking Spot 12"
    type = Column(String, nullable=False) # "desk", "parking", "equipment", "room"
    location = Column(String, nullable=True) # e.g. "Floor 2, North Wing"
    status = Column(String, default="available") # available, maintenance
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    bookings = relationship("AssetBooking", back_populates="asset", cascade="all, delete-orphan")

class AssetBooking(Base):
    __tablename__ = "ops_bookings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String, ForeignKey("ops_assets.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(String, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, default="confirmed") # confirmed, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    asset = relationship("FacilityAsset", back_populates="bookings")

class VisitorLog(Base):
    __tablename__ = "ops_visitors"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    visitor_name = Column(String, nullable=False)
    company = Column(String, nullable=True)
    host_id = Column(String, ForeignKey("users.id"), nullable=False)
    expected_arrival = Column(DateTime(timezone=True), nullable=False)
    check_in_time = Column(DateTime(timezone=True), nullable=True)
    check_out_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="expected") # expected, checked_in, checked_out
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class MaintenanceRequest(Base):
    __tablename__ = "ops_maintenance_requests"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    asset_id = Column(String, ForeignKey("ops_assets.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    priority = Column(String(20), default="medium")  # low/medium/high/critical
    status = Column(String(20), default="reported")  # reported/in_progress/resolved/closed
    reported_by_id = Column(String(100), nullable=False)
    assigned_to_id = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    asset = relationship("FacilityAsset", backref="maintenance_requests")
