from sqlalchemy import String, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
import uuid
from app.models.base import Base
from app.core.encryption import encrypt_key, decrypt_key

class Team(Base):
    """
    Equipos de trabajo dentro de la organización.
    """
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class TeamMember(Base):
    """
    Miembros asignados a un equipo de trabajo.
    """
    __tablename__ = "team_members"

    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    team_id: Mapped[str] = mapped_column(String, ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ChatRoom(Base):
    """
    Salas de chat correspondientes a DMs, Departamentos, Equipos o Jerarquías.
    """
    __tablename__ = "chat_rooms"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    name: Mapped[str] = mapped_column(String(255), nullable=True) # Nombre visible del canal (nulo para DMs)
    room_type: Mapped[str] = mapped_column(String(50), default="DIRECT") # DIRECT, DEPARTMENT, TEAM, HIERARCHY
    
    department: Mapped[str] = mapped_column(String(100), nullable=True) # Si es canal de departamento
    team_id: Mapped[str] = mapped_column(String, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True) # Si es canal de equipo
    manager_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True) # Si es canal de jerarquía (reportes directos)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ChatRoomMember(Base):
    """
    Usuarios miembros de una sala de chat.
    """
    __tablename__ = "chat_room_members"

    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    room_id: Mapped[str] = mapped_column(String, ForeignKey("chat_rooms.id", ondelete="CASCADE"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    unread_count: Mapped[int] = mapped_column(Integer, default=0)


class ChatMessage(Base):
    """
    Mensajes de chat encriptados en base de datos.
    """
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    room_id: Mapped[str] = mapped_column(String, ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False)
    sender_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    encrypted_content: Mapped[str] = mapped_column(String, nullable=False)
    attachment_url: Mapped[str] = mapped_column(String(500), nullable=True)
    attachment_name: Mapped[str] = mapped_column(String(255), nullable=True)
    parent_id: Mapped[str] = mapped_column(String, ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True)
    reactions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    @property
    def content(self) -> str:
        return decrypt_key(self.encrypted_content)

    @content.setter
    def content(self, value: str):
        self.encrypted_content = encrypt_key(value)

    @property
    def reply_count(self) -> int:
        return 0
