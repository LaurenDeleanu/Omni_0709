from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Numeric, Text, ForeignKey, Boolean, Integer
from datetime import datetime, timezone
import uuid
from app.models.base import Base


class Course(Base):
    """
    Curso del catálogo formativo. Soporta cursos estándar y paquetes SCORM.
    """
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_scorm: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scorm_version: Mapped[str] = mapped_column(String(20), nullable=True)  # "1.2" o "2004"
    package_url: Mapped[str] = mapped_column(String(500), nullable=True)  # URL de descarga/carga
    min_duration_hours: Mapped[float] = mapped_column(Numeric(6, 2), default=2.0, nullable=False)  # Requisito FUNDAE
    is_fundae_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CourseEnrollment(Base):
    """
    Matrícula y avance de un empleado en un curso.
    Almacena variables de estado SCORM en tiempo de ejecución.
    """
    __tablename__ = "course_enrollments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="enrolled", nullable=False)  # enrolled, in_progress, completed
    progress_percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0, nullable=False)
    scorm_suspend_data: Mapped[str] = mapped_column(Text, nullable=True)  # suspend_data de SCORM
    score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=True)  # Puntuación final
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class FundaeValidation(Base):
    """
    Registro de cumplimiento normativo de FUNDAE para una matrícula específica.
    """
    __tablename__ = "fundae_validations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    enrollment_id: Mapped[str] = mapped_column(String, ForeignKey("course_enrollments.id", ondelete="CASCADE"), unique=True, nullable=False)
    duration_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # >= min_duration_hours
    progress_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # >= 75% completado
    test_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Test superado
    survey_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Encuesta satisfacción
    overall_eligible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # ¿Bono aplicable?
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
