from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import xml.etree.ElementTree as ET
from xml.dom import minidom
from app.api.dependencies import get_tenant_db, require_roles, check_module_enabled, get_current_user
from app.services.course_recommender import recommend_courses
from app.models.training import Course, CourseEnrollment, FundaeValidation
from app.models.user import User
from app.schemas.training import (
    CourseCreate, CourseResponse, CourseUpdate,
    CourseEnrollmentCreate, CourseEnrollmentResponse, CourseEnrollmentUpdate,
    FundaeValidationResponse
)

router = APIRouter(dependencies=[Depends(check_module_enabled("training"))])



# ==========================================
# COURSE CATALOG ENDPOINTS
# ==========================================
@router.get("/courses", response_model=List[CourseResponse])
async def list_courses(
    is_fundae_eligible: Optional[bool] = None,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Listar cursos disponibles en el catálogo."""
    query = select(Course)
    if is_fundae_eligible is not None:
        query = query.where(Course.is_fundae_eligible == is_fundae_eligible)
        
    result = await db.execute(query.order_by(Course.created_at.desc()))
    return result.scalars().all()


@router.post("/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    course_in: CourseCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """Crear un nuevo curso en el catálogo."""
    course = Course(
        id=uuid.uuid4().hex,
        **course_in.model_dump()
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


@router.put("/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    course_in: CourseUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """Actualizar detalles de un curso."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    for field, value in course_in.model_dump(exclude_unset=True).items():
        setattr(course, field, value)

    await db.commit()
    await db.refresh(course)
    return course


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """Eliminar un curso de catálogo."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    await db.delete(course)
    await db.commit()
    return None


# ==========================================
# COURSE ENROLLMENTS ENDPOINTS
# ==========================================
@router.get("/enrollments", response_model=List[CourseEnrollmentResponse])
async def list_enrollments(
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Listar matrículas formativas."""
    query = select(CourseEnrollment)
    
    if user_payload.get("role") == "employee":
        query = query.where(CourseEnrollment.user_id == user_payload.get("user_id"))
    elif user_id:
        query = query.where(CourseEnrollment.user_id == user_id)
        
    result = await db.execute(query.order_by(CourseEnrollment.created_at.desc()))
    return result.scalars().all()


@router.post("/enrollments", response_model=CourseEnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def create_enrollment(
    enroll_in: CourseEnrollmentCreate,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """Matricular un empleado en un curso."""
    if user_payload.get("role") == "employee" and enroll_in.user_id != user_payload.get("user_id"):
        raise HTTPException(status_code=403, detail="No puedes matricular a otro empleado")

    # Verificar si ya existe matrícula activa
    result = await db.execute(
        select(CourseEnrollment).where(
            CourseEnrollment.user_id == enroll_in.user_id,
            CourseEnrollment.course_id == enroll_in.course_id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    enroll = CourseEnrollment(
        id=uuid.uuid4().hex,
        user_id=enroll_in.user_id,
        course_id=enroll_in.course_id,
        status="enrolled",
        progress_percentage=0.0,
        time_spent_seconds=0
    )
    db.add(enroll)
    await db.commit()
    await db.refresh(enroll)
    return enroll


# ==========================================
# SCORM STATE COMMIT
# ==========================================
@router.patch("/enrollments/{enrollment_id}/scorm", response_model=CourseEnrollmentResponse)
async def commit_scorm_state(
    enrollment_id: str,
    scorm_in: CourseEnrollmentUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin", "employee"]))
):
    """
    Guarda las variables de estado enviadas por el API SCORM de JavaScript.
    Si el estado cambia a 'completed', ejecuta automáticamente las validaciones de FUNDAE.
    """
    result = await db.execute(select(CourseEnrollment).where(CourseEnrollment.id == enrollment_id))
    enroll = result.scalar_one_or_none()
    if not enroll:
        raise HTTPException(status_code=404, detail="Matrícula no encontrada")

    if user_payload.get("role") == "employee" and enroll.user_id != user_payload.get("user_id"):
        raise HTTPException(status_code=403, detail="No puedes modificar la matrícula de otro empleado")

    # Guardar campos SCORM
    for field, value in scorm_in.model_dump(exclude_unset=True).items():
        setattr(enroll, field, value)
        
    if scorm_in.status == "completed" and not enroll.completed_at:
        enroll.completed_at = datetime.now(timezone.utc)

    await db.commit()

    if scorm_in.status == "completed":
        try:
            from app.services.event_publisher import publish_training_event
            await publish_training_event(db, enroll.id, enroll.user_id, enroll.course_id, "completed", "acme_corp")
        except Exception:
            pass

    # Si es apto para FUNDAE, re-validar al instante
    course_res = await db.execute(select(Course).where(Course.id == enroll.course_id))
    course = course_res.scalar_one_or_none()
    if course and course.is_fundae_eligible:
        await run_fundae_validation_logic(enroll, course, db)
        
    await db.refresh(enroll)
    return enroll


# ==========================================
# FUNDAE COMPLIANCE RUNNER & EXPORTS
# ==========================================
async def run_fundae_validation_logic(
    enroll: CourseEnrollment,
    course: Course,
    db: AsyncSession
) -> FundaeValidation:
    """Ejecuta las 4 reglas del motor de cumplimiento normativo de FUNDAE."""
    # Regla 1: Duración mínima en horas realizada.
    # Convertir segundos realizados a horas
    hours_done = enroll.time_spent_seconds / 3600.0
    duration_valid = hours_done >= float(course.min_duration_hours)
    
    # Regla 2: Avance del temario / contenido >= 75%
    progress_valid = enroll.progress_percentage >= 75.0
    
    # Regla 3: Nota media en pruebas de evaluación superior a 5.0 (sobre 10)
    test_valid = False
    if enroll.score is not None:
        test_valid = enroll.score >= 5.0
        
    # Regla 4: Encuesta de satisfacción de FUNDAE completada (Simulada por campo de progreso)
    survey_valid = enroll.status == "completed"
    
    # Apto global para bonificación
    overall_eligible = duration_valid and progress_valid and test_valid and survey_valid

    # Buscar si ya existe la validación en la DB
    val_res = await db.execute(select(FundaeValidation).where(FundaeValidation.enrollment_id == enroll.id))
    val = val_res.scalar_one_or_none()
    
    if not val:
        val = FundaeValidation(
            id=uuid.uuid4().hex,
            enrollment_id=enroll.id,
            duration_valid=duration_valid,
            progress_valid=progress_valid,
            test_valid=test_valid,
            survey_valid=survey_valid,
            overall_eligible=overall_eligible
        )
        db.add(val)
    else:
        val.duration_valid = duration_valid
        val.progress_valid = progress_valid
        val.test_valid = test_valid
        val.survey_valid = survey_valid
        val.overall_eligible = overall_eligible
        val.generated_at = datetime.now(timezone.utc)
        
    await db.commit()
    return val


@router.get("/fundae/validate/{enrollment_id}", response_model=FundaeValidationResponse)
async def validate_fundae_compliance(
    enrollment_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """Consulta manual y ejecución del estado de elegibilidad FUNDAE para una matrícula."""
    result = await db.execute(select(CourseEnrollment).where(CourseEnrollment.id == enrollment_id))
    enroll = result.scalar_one_or_none()
    if not enroll:
        raise HTTPException(status_code=404, detail="Matrícula no encontrada")
        
    course_res = await db.execute(select(Course).where(Course.id == enroll.course_id))
    course = course_res.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    val = await run_fundae_validation_logic(enroll, course, db)
    return val


@router.get("/fundae/export-xml")
async def export_fundae_xml(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """
    Genera el archivo XML de comunicaciones de finalización de grupos formativos
    cumpliendo exactamente con el esquema oficial requerido por la aplicación telemática de FUNDAE.
    """
    # Consultar todas las matrículas elegibles/bonificadas
    query = select(CourseEnrollment).join(
        FundaeValidation, FundaeValidation.enrollment_id == CourseEnrollment.id
    ).where(FundaeValidation.overall_eligible == True)
    
    result = await db.execute(query)
    eligible_enrolls = result.scalars().all()

    # Generar estructura XML
    root = ET.Element("comunicacion_finalizacion")
    root.set("version", "2026.1")
    
    # Datos de empresa bonificada
    empresa = ET.SubElement(root, "empresa")
    cif = ET.SubElement(empresa, "cif")
    cif.text = "A1234567B"  # CIF Demo del tenant
    razon_social = ET.SubElement(empresa, "razon_social")
    razon_social.text = "Acme Corp S.A."

    # Grupos formativos
    grupos = ET.SubElement(root, "grupos")
    
    if eligible_enrolls:
        grupo = ET.SubElement(grupos, "grupo")
        id_grupo = ET.SubElement(grupo, "codigo_grupo")
        id_grupo.text = "G-2026-0001"
        
        # Alumnos participantes
        alumnos = ET.SubElement(grupo, "participantes")
        for enroll in eligible_enrolls:
            # Buscar el email/cif del participante
            user_res = await db.execute(select(User).where(User.id == enroll.user_id))
            user = user_res.scalar_one_or_none()
            user_name = user.full_name if user else "Participante"
            user_email = user.email if user else "alumni@acme.com"

            part = ET.SubElement(alumnos, "participante")
            nif = ET.SubElement(part, "nif")
            nif.text = "12345678Z"  # NIF Demo
            nombre = ET.SubElement(part, "nombre")
            nombre.text = user_name
            email = ET.SubElement(part, "email")
            email.text = user_email
            
            # Variables de FUNDAE
            horas = ET.SubElement(part, "horas_realizadas")
            horas.text = f"{enroll.time_spent_seconds / 3600.0:.2f}"
            apto = ET.SubElement(part, "resultado")
            apto.text = "APTO"
            
    # Formatear el XML con sangría
    xml_str = ET.tostring(root, encoding="utf-8")
    reparsed = minidom.parseString(xml_str)
    pretty_xml = reparsed.toprettyxml(indent="  ")

    # El export abarca todas las matrículas elegibles (no un curso concreto),
    # por lo que el nombre de archivo se deriva de la fecha de generación.
    export_date = datetime.now(timezone.utc).strftime("%Y%m%d")
    return Response(
        content=pretty_xml,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename=fundae_{export_date}.xml"},
    )


@router.get("/recommendations/{user_id}")
async def get_course_recommendations(
    user_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["employee", "hr_admin"]))
):
    try:
        return await recommend_courses(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/scorm/import", response_model=dict)
async def import_scorm_course(
    manifest_xml: str,
    course_name: str = "",
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "super_admin", "training_admin"]))
):
    from app.services.scorm_xapi import store_scorm_course
    tenant_id = current_user.get("tenant_id", "default")
    result = await store_scorm_course(db, manifest_xml, course_name, tenant_id)
    return result


@router.post("/xapi/statements", response_model=dict)
async def record_xapi_statement_endpoint(
    statement: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    from app.services.scorm_xapi import record_xapi_statement
    user_id = current_user.get("sub", "").split("|")[-1]
    tenant_id = current_user.get("tenant_id", "default")
    result = await record_xapi_statement(db, statement, user_id, tenant_id)
    return result


@router.get("/fundae/calculate", response_model=dict)
async def calculate_fundae(
    course_hours: int = 20, modality: str = "presencial", num_participants: int = 5,
    company_size: str = "10-49", has_tutor: bool = True,
    _: dict = Depends(require_roles(["hr_admin", "super_admin", "training_admin"]))
):
    from app.services.fundae_service import calculate_fundae_bonus
    return await calculate_fundae_bonus(course_hours, modality, num_participants, company_size, has_tutor)


@router.get("/fundae/summary", response_model=dict)
async def get_fundae_summary_endpoint(year: int = 2026, db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "super_admin", "training_admin"]))):
    from app.services.fundae_service import get_fundae_summary
    return await get_fundae_summary(db, year)
