from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, JSON, UniqueConstraint
from datetime import datetime, timezone
import uuid
from app.models.base import Base

class PageMetadata(Base):
    """
    Guarda la configuración dinámica de una página/módulo basada en metadatos.
    Ejemplo de schema JSON: { "layout": "table", "fields": [...] }
    """
    __tablename__ = "page_metadata"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    module_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    page_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    schema_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("module_name", "page_name", name="uix_module_page"),
    )
