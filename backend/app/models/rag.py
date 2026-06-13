from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
from datetime import datetime, timezone
import uuid
from app.models.base import Base
from pgvector.sqlalchemy import Vector

class KnowledgeDocument(Base):
    """
    Documentos cargados al Agente para su base de conocimiento (RAG).
    """
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    agent = relationship("Agent", back_populates="knowledge_docs")
    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")

class KnowledgeChunk(Base):
    """
    Fragmentos indexados y vectorizados de un documento de conocimiento.
    """
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    document_id: Mapped[str] = mapped_column(String, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Columna de vector usando pgvector
    embedding = mapped_column(Vector(1536), nullable=True)

    chunk_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)

    # Relationships
    document = relationship("KnowledgeDocument", back_populates="chunks")
