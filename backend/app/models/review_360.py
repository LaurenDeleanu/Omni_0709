from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, JSON, Integer, Float, Boolean, Text
from datetime import datetime, timezone
from typing import Optional
import uuid
from app.models.base import Base


class ReviewCycle(Base):
    __tablename__ = "review_cycles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    review_type: Mapped[str] = mapped_column(String(50), default="360")
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[str]] = mapped_column(String)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    reviews = relationship("Review", back_populates="cycle", cascade="all, delete-orphan")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    cycle_id: Mapped[str] = mapped_column(String, ForeignKey("review_cycles.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    reviewer_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(50), default="peer")
    status: Mapped[str] = mapped_column(String(50), default="pending")
    overall_rating: Mapped[Optional[float]] = mapped_column(Float)
    strengths: Mapped[Optional[str]] = mapped_column(Text)
    improvements: Mapped[Optional[str]] = mapped_column(Text)
    comments: Mapped[Optional[str]] = mapped_column(Text)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    cycle = relationship("ReviewCycle", back_populates="reviews")
    ratings = relationship("ReviewRating", back_populates="review", cascade="all, delete-orphan")


class ReviewRating(Base):
    __tablename__ = "review_ratings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    review_id: Mapped[str] = mapped_column(String, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    review = relationship("Review", back_populates="ratings")


DEFAULT_CATEGORIES = [
    {"key": "communication", "label": "Communication", "description": "Clearly expresses ideas and actively listens"},
    {"key": "teamwork", "label": "Teamwork", "description": "Collaborates effectively with colleagues"},
    {"key": "leadership", "label": "Leadership", "description": "Guides and inspires others"},
    {"key": "problem_solving", "label": "Problem Solving", "description": "Analyzes issues and finds effective solutions"},
    {"key": "reliability", "label": "Reliability", "description": "Consistently delivers on commitments"},
    {"key": "innovation", "label": "Innovation", "description": "Brings new ideas and improves processes"},
    {"key": "technical_skills", "label": "Technical Skills", "description": "Demonstrates required technical expertise"},
    {"key": "customer_focus", "label": "Customer Focus", "description": "Prioritizes internal/external customer needs"},
]
