from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Boolean, ForeignKey, JSON
from datetime import datetime, timezone
import uuid
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    department: Mapped[str] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[str] = mapped_column(String(50), default="employee")
    roles: Mapped[list] = mapped_column(JSON, default=lambda: ["employee"], nullable=False)
    role_id: Mapped[str] = mapped_column(String, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    manager_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    vacation_allowance: Mapped[int] = mapped_column(default=30)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=True)
    current_debt: Mapped[float] = mapped_column(default=0.0, nullable=False)
    base_salary: Mapped[float] = mapped_column(default=0.0)
    country: Mapped[str] = mapped_column(String(2), default="ES")
    timezone: Mapped[str] = mapped_column(String(100), default="Europe/Madrid")
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    locale: Mapped[str] = mapped_column(String(10), default="es")
    phone_number: Mapped[str] = mapped_column(String(50), nullable=True)

    _address: Mapped[str] = mapped_column("address", String(255), nullable=True)
    _iban: Mapped[str] = mapped_column("iban", String(100), nullable=True)
    _social_security_number: Mapped[str] = mapped_column("social_security_number", String(50), nullable=True)

    emergency_contact: Mapped[str] = mapped_column(String(255), nullable=True)
    contract_type: Mapped[str] = mapped_column(String(100), default="Indefinido", nullable=True)
    hire_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=True)
    custom_fields: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @property
    def address(self) -> str:
        return self._decrypt(self._address) if self._address else ""

    @address.setter
    def address(self, value: str):
        self._address = self._encrypt(value) if value else None

    @property
    def iban(self) -> str:
        return self._decrypt(self._iban) if self._iban else ""

    @iban.setter
    def iban(self, value: str):
        self._iban = self._encrypt(value) if value else None

    @property
    def social_security_number(self) -> str:
        return self._decrypt(self._social_security_number) if self._social_security_number else ""

    @social_security_number.setter
    def social_security_number(self, value: str):
        self._social_security_number = self._encrypt(value) if value else None

    @staticmethod
    def _encrypt(value: str) -> str:
        from app.services.field_encryption import encrypt_field
        return encrypt_field(value)

    @staticmethod
    def _decrypt(value: str) -> str:
        from app.services.field_encryption import decrypt_field
        return decrypt_field(value)


class ProfileChangeRequest(Base):
    """
    Solicitudes de cambios en datos personales y sensibles pendientes de aprobación por RRHH.
    """
    __tablename__ = "profile_change_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(50), nullable=False) # 'iban' o 'address'
    old_value: Mapped[str] = mapped_column(String(255), nullable=True)
    new_value: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, rejected
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String(36), nullable=True)


class SkillProfile(Base):
    """
    Perfil de habilidades y competencias técnicas o blandas de un empleado.
    """
    __tablename__ = "skill_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    level: Mapped[int] = mapped_column(default=1, nullable=False)  # 1 to 5
    source: Mapped[str] = mapped_column(String(50), default="self", nullable=False)  # resume, review, course, manager, self
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


