from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Float, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import Optional
import uuid
from app.models.base import Base

class JobPosting(Base):
    __tablename__ = "hire_jobs"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    title = Column(String(150), nullable=False)
    department = Column(String(100))
    location = Column(String(100))
    employment_type = Column(String(50)) # e.g., Full-time, Part-time, Contract
    description = Column(Text)
    status = Column(String(50), default="open") # open, closed, draft
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    candidates = relationship("Candidate", back_populates="job", cascade="all, delete-orphan")

class Candidate(Base):
    __tablename__ = "hire_candidates"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    job_id = Column(String(36), ForeignKey("hire_jobs.id"), nullable=False)
    
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50))
    
    resume_url = Column(String(500))
    linkedin_url = Column(String(255))
    portfolio_url = Column(String(255))
    
    stage = Column(String(50), default="applied") # applied, screening, interview, offer, hired, rejected
    source = Column(String(100)) # e.g., LinkedIn, Referrals, Website
    notes = Column(Text)

    last_contacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    engagement_score: Mapped[float] = mapped_column(Float, default=0.0)
    source_detail: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    job = relationship("JobPosting", back_populates="candidates")
    interviews = relationship("Interview", back_populates="candidate", cascade="all, delete-orphan")
    pool_entries = relationship("CandidatePoolEntry", back_populates="candidate", cascade="all, delete-orphan")

class Interview(Base):
    __tablename__ = "hire_interviews"

    id = Column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    candidate_id = Column(String(36), ForeignKey("hire_candidates.id"), nullable=False)
    interviewer_id = Column(String(36), ForeignKey("users.id")) # Links to our employee table
    
    scheduled_at = Column(DateTime(timezone=True))
    duration_minutes = Column(Integer, default=60)
    interview_type = Column(String(50)) # e.g., Technical, Cultural, HR
    feedback_notes = Column(Text)
    score = Column(Float) # e.g., 1 to 5
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    candidate = relationship("Candidate", back_populates="interviews")
    interviewer = relationship("User")

class CandidatePool(Base):
    __tablename__ = "hire_candidate_pools"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    entries = relationship("CandidatePoolEntry", back_populates="pool", cascade="all, delete-orphan")

class CandidatePoolEntry(Base):
    __tablename__ = "hire_candidate_pool_entries"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    pool_id: Mapped[str] = mapped_column(String, ForeignKey("hire_candidate_pools.id", ondelete="CASCADE"))
    candidate_id: Mapped[str] = mapped_column(String, ForeignKey("hire_candidates.id", ondelete="CASCADE"))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    engagement_score: Mapped[float] = mapped_column(Float, default=0.0)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    pool = relationship("CandidatePool", back_populates="entries")
    candidate = relationship("Candidate", back_populates="pool_entries")
