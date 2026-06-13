from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, JSON, Integer, Float
from datetime import datetime, timezone
import uuid
from app.models.base import Base

class TestSuite(Base):
    """
    Agrupación de casos de prueba para evaluar la calidad y seguridad de un Agente.
    """
    __tablename__ = "test_suites"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    agent = relationship("Agent", back_populates="test_suites")
    test_cases = relationship("TestCase", back_populates="suite", cascade="all, delete-orphan")
    runs = relationship("TestRun", back_populates="suite", cascade="all, delete-orphan")

class TestCase(Base):
    """
    Caso de prueba individual para evaluar comportamiento conversacional.
    """
    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    suite_id: Mapped[str] = mapped_column(String, ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_payload: Mapped[str] = mapped_column(String, nullable=False) # Frase simulada del usuario
    expected_criteria: Mapped[str] = mapped_column(String, nullable=False) # Instrucción al Evaluador
    mock_collected_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False) # Datos mocked
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    suite = relationship("TestSuite", back_populates="test_cases")

class TestRun(Base):
    """
    Historial de ejecuciones de un suite de pruebas evaluado por LLM-as-a-Judge.
    """
    __tablename__ = "test_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    suite_id: Mapped[str] = mapped_column(String, ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False, index=True)
    
    status: Mapped[str] = mapped_column(String(50), nullable=False) # SUCCESS, FAILED
    passed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    log_details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False) # JSON list of details: [{case_id, score, critique}]
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    suite = relationship("TestSuite", back_populates="runs")
