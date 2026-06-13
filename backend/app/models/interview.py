from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Integer, Text, Float, JSON
from datetime import datetime, timezone
import uuid
from app.models.base import Base
from typing import List, Optional


class InterviewScorecard(Base):
    __tablename__ = "interview_scorecards"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_title: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    criteria: Mapped[List["ScorecardCriterion"]] = relationship(back_populates="scorecard", cascade="all, delete-orphan")


class ScorecardCriterion(Base):
    __tablename__ = "scorecard_criteria"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    scorecard_id: Mapped[str] = mapped_column(String, ForeignKey("interview_scorecards.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    max_score: Mapped[int] = mapped_column(Integer, default=5)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    scorecard: Mapped["InterviewScorecard"] = relationship(back_populates="criteria")


class InterviewKit(Base):
    __tablename__ = "interview_kits"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_title: Mapped[str] = mapped_column(String(255), nullable=False)
    scorecard_id: Mapped[str] = mapped_column(String, ForeignKey("interview_scorecards.id", ondelete="SET NULL"), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    total_duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    stages: Mapped[List["InterviewStage"]] = relationship(back_populates="kit", cascade="all, delete-orphan")


class InterviewStage(Base):
    __tablename__ = "interview_stages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    kit_id: Mapped[str] = mapped_column(String, ForeignKey("interview_kits.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    interviewer_role: Mapped[str] = mapped_column(String(50), default="recruiter")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    suggested_questions: Mapped[dict] = mapped_column(JSON, default=list)
    evaluation_focus: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    kit: Mapped["InterviewKit"] = relationship(back_populates="stages")


class CandidateEvaluation(Base):
    __tablename__ = "candidate_evaluations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    candidate_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    scorecard_id: Mapped[str] = mapped_column(String, ForeignKey("interview_scorecards.id", ondelete="SET NULL"), nullable=True)
    kit_id: Mapped[str] = mapped_column(String, ForeignKey("interview_kits.id", ondelete="SET NULL"), nullable=True)
    interviewer_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    stage_name: Mapped[str] = mapped_column(String(255), nullable=True)
    overall_notes: Mapped[str] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str] = mapped_column(String(30), default="consider")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    scores: Mapped[List["CriterionScore"]] = relationship(back_populates="evaluation", cascade="all, delete-orphan")


class CriterionScore(Base):
    __tablename__ = "criterion_scores"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    evaluation_id: Mapped[str] = mapped_column(String, ForeignKey("candidate_evaluations.id", ondelete="CASCADE"), nullable=False)
    criterion_id: Mapped[str] = mapped_column(String, ForeignKey("scorecard_criteria.id", ondelete="CASCADE"), nullable=False)
    criterion_name: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    evaluation: Mapped["CandidateEvaluation"] = relationship(back_populates="scores")
