import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text

from app.models.base import Base


class BranchSession(Base):
    __tablename__ = "branch_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    branch_name: Mapped[str] = mapped_column(String, nullable=False)
    base_branch: Mapped[str] = mapped_column(String, default="main")
    status: Mapped[str] = mapped_column(String, default="active")
    total_proposals: Mapped[int] = mapped_column(Integer, default=0)
    applied_proposals: Mapped[int] = mapped_column(Integer, default=0)
    rejected_proposals: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    proposals = relationship("FileProposal", back_populates="session", cascade="all, delete-orphan")


class FileProposal(Base):
    __tablename__ = "file_proposals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    branch_session_id: Mapped[str] = mapped_column(String, ForeignKey("branch_sessions.id"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_content: Mapped[str] = mapped_column(Text, nullable=False)
    diff_text: Mapped[str] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    proposed_by: Mapped[str] = mapped_column(String, nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String, nullable=True)
    review_notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    session = relationship("BranchSession", back_populates="proposals")
