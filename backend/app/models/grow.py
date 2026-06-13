from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.models.base import Base

class Objective(Base):
    __tablename__ = "grow_objectives"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(String, ForeignKey("users.id"))
    status = Column(String, default="On Track")
    parent_id = Column(String, ForeignKey("grow_objectives.id"), nullable=True)
    department = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    key_results = relationship("KeyResult", back_populates="objective", cascade="all, delete-orphan")

class KeyResult(Base):
    __tablename__ = "grow_key_results"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    objective_id = Column(String, ForeignKey("grow_objectives.id", ondelete="CASCADE"))
    title = Column(String, nullable=False)
    target_value = Column(Integer, nullable=False)
    current_value = Column(Integer, default=0)
    unit = Column(String, default="%") # e.g. "%", "eur", "units"
    
    objective = relationship("Objective", back_populates="key_results")

class PerformanceReview(Base):
    __tablename__ = "grow_reviews"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String, ForeignKey("users.id"))
    manager_id = Column(String, ForeignKey("users.id"))
    cycle_name = Column(String, nullable=False) # e.g. "Q1 2026 Review"
    status = Column(String, default="Draft") # "Draft", "Self Evaluation", "Manager Evaluation", "Completed"
    self_evaluation = Column(JSON, nullable=True)
    manager_evaluation = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    nominations = relationship("ReviewNomination", back_populates="review", cascade="all, delete-orphan")
    responses = relationship("ReviewResponse", back_populates="review", cascade="all, delete-orphan")

class ReviewNomination(Base):
    __tablename__ = "grow_review_nominations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id = Column(String, ForeignKey("grow_reviews.id", ondelete="CASCADE"))
    nominator_id = Column(String, ForeignKey("users.id"))
    nominee_id = Column(String, ForeignKey("users.id"))
    relationship_type = Column(String) # "peer", "direct_report", "manager", "other"
    status = Column(String, default="Pending") # "Pending", "Approved", "Rejected"
    
    review = relationship("PerformanceReview", back_populates="nominations")

class ReviewResponse(Base):
    __tablename__ = "grow_review_responses"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id = Column(String, ForeignKey("grow_reviews.id", ondelete="CASCADE"))
    reviewer_id = Column(String, ForeignKey("users.id"))
    relationship_type = Column(String) # "peer", "direct_report", "manager", "self"
    status = Column(String, default="Draft") # "Draft", "Submitted"
    feedback = Column(JSON, nullable=True)
    is_anonymous = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    
    review = relationship("PerformanceReview", back_populates="responses")
