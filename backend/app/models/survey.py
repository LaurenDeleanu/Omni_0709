from sqlalchemy import Column, String, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.models.base import Base

class PulseSurvey(Base):
    __tablename__ = "pulse_surveys"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="draft") # draft, active, closed
    questions = Column(JSON, nullable=False) # e.g. [{"id": "q1", "text": "How are you?", "type": "rating"}]
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    responses = relationship("PulseResponse", back_populates="survey", cascade="all, delete-orphan")

class PulseResponse(Base):
    __tablename__ = "pulse_responses"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    survey_id = Column(String, ForeignKey("pulse_surveys.id", ondelete="CASCADE"))
    user_id = Column(String, ForeignKey("users.id"))
    answers = Column(JSON, nullable=False) # e.g. {"q1": 5, "q2": "I'm doing well"}
    submitted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    survey = relationship("PulseSurvey", back_populates="responses")
