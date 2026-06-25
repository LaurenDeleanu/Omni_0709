from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text
from app.models.base import Base
from pgvector.sqlalchemy import Vector
import uuid

class SearchIndexEntry(Base):
    __tablename__ = "search_index_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # "employee", "agent", "project", "course", "job"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtitle: Mapped[str] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    route: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding = mapped_column(Vector(1536), nullable=True)
