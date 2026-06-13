from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Table, Column
from datetime import datetime, timezone
import uuid
from app.models.base import Base

class Role(Base):
    """
    Custom roles created by the Tenant Admin to assign granular access control.
    """
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    is_system_default: Mapped[bool] = mapped_column(Boolean, default=False) # e.g. "Employee", "HR Admin" cannot be deleted
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relations
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")

class Permission(Base):
    """
    System-defined permissions that can be granted to roles (e.g., 'users:read', 'it_assets:write').
    """
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    module: Mapped[str] = mapped_column(String(50), index=True, nullable=False) # e.g., 'people', 'finance', 'it'
    action: Mapped[str] = mapped_column(String(50), nullable=False) # e.g., 'create', 'read', 'update', 'delete', 'manage'
    description: Mapped[str] = mapped_column(String(255), nullable=True)

class RolePermission(Base):
    """
    Association table linking Roles to Permissions.
    """
    __tablename__ = "role_permissions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    role_id: Mapped[str] = mapped_column(String, ForeignKey("roles.id", ondelete="CASCADE"), index=True, nullable=False)
    permission_id: Mapped[str] = mapped_column(String, ForeignKey("permissions.id", ondelete="CASCADE"), index=True, nullable=False)

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission")
