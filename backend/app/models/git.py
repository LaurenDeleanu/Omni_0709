from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, JSON, Text
from datetime import datetime, timezone
import uuid
from app.models.base import Base
from app.core.encryption import encrypt_key, decrypt_key

class GitRepository(Base):
    __tablename__ = "git_repositories"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    provider: Mapped[str] = mapped_column(String(50), default="github", nullable=False)
    repo_url: Mapped[str] = mapped_column(String(255), nullable=False)

    _access_token: Mapped[str] = mapped_column("access_token", String(500), nullable=True)

    default_branch: Mapped[str] = mapped_column(String(100), default="main", nullable=False)
    dev_branch: Mapped[str] = mapped_column(String(100), default="dev", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    modules = relationship("CodeModule", back_populates="repo", cascade="all, delete-orphan")

    @property
    def access_token(self) -> str:
        return decrypt_key(self._access_token) if self._access_token else ""

    @access_token.setter
    def access_token(self, value: str):
        self._access_token = encrypt_key(value) if value else None

class CodeModule(Base):
    """
    Módulo de código generado por un agente de IA y pendiente de revisión/PR.
    """
    __tablename__ = "code_modules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    repo_id: Mapped[str] = mapped_column(String, ForeignKey("git_repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Lista de archivos generados en formato JSON: [{path: string, content: string, language: string}]
    files: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False) # draft, review, approved, merged
    branch_name: Mapped[str] = mapped_column(String(255), nullable=True)
    pr_url: Mapped[str] = mapped_column(String(255), nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String(100), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    repo = relationship("GitRepository", back_populates="modules")
    agent = relationship("Agent", back_populates="code_modules")
