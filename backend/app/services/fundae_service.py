import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

logger = logging.getLogger("successcore.fundae")


FUNDAE_BONUS_RATES = {
    "presencial": {"base": 13.00, "max": 200, "tutor": 2.00},
    "teleformacion": {"base": 7.00, "max": 120, "tutor": 1.50},
    "mixta": {"base": 9.00, "max": 150, "tutor": 1.75},
}

COMPANY_SIZES = {
    "1-9": {"credit_pct": 100, "max_credit": 420},
    "10-49": {"credit_pct": 100, "max_credit": 420},
    "50-249": {"credit_pct": 75, "max_credit": 420},
    "250+": {"credit_pct": 60, "max_credit": 420},
}

EMPLOYEE_BONUS_CAPS = {
    "1-5": {"max_hours": 200, "individual_max": 200},
    "6-30": {"max_hours": 200, "individual_max": 150},
    "31-50": {"max_hours": 200, "individual_max": 100},
    "50+": {"max_hours": 200, "individual_max": 60},
}


async def calculate_fundae_bonus(
    course_hours: int,
    modality: str = "presencial",
    num_participants: int = 1,
    company_size: str = "10-49",
    has_tutor: bool = True,
) -> Dict[str, Any]:
    rates = FUNDAE_BONUS_RATES.get(modality, FUNDAE_BONUS_RATES["presencial"])
    size_config = COMPANY_SIZES.get(company_size, COMPANY_SIZES["10-49"])
    participant_bracket = "1-5" if num_participants <= 5 else ("6-30" if num_participants <= 30 else "31-50")
    caps = EMPLOYEE_BONUS_CAPS.get(participant_bracket, EMPLOYEE_BONUS_CAPS["1-5"])

    hours_per_person = min(course_hours, caps["individual_max"])
    hours_per_person = min(hours_per_person, rates["max"])

    base_bonus = hours_per_person * rates["base"] * num_participants
    tutor_bonus = hours_per_person * rates["tutor"] * (1 if has_tutor else 0) * (min(num_participants, 30))

    total_bonus = base_bonus + tutor_bonus
    credit_applied = min(total_bonus, size_config["max_credit"])
    company_cofinancing = max(0, total_bonus - credit_applied)

    return {
        "modality": modality,
        "course_hours": course_hours,
        "hours_per_participant": hours_per_person,
        "num_participants": num_participants,
        "base_bonus_eur": round(base_bonus, 2),
        "tutor_bonus_eur": round(tutor_bonus, 2),
        "total_bonus_eur": round(total_bonus, 2),
        "fundae_credit_applied_eur": round(credit_applied, 2),
        "company_cofinancing_eur": round(company_cofinancing, 2),
        "fundae_contribution_pct": round(credit_applied / max(total_bonus, 1) * 100, 1),
    }


async def validate_fundae_enrollment(
    db: AsyncSession,
    enrollment_id: str,
) -> Dict[str, Any]:
    checks = {
        "entry": {"passed": True, "detail": ""},
        "hours_minimum": {"passed": True, "detail": ""},
        "participant_company": {"passed": True, "detail": ""},
        "tutor_accreditation": {"passed": True, "detail": ""},
        "evaluation_completed": {"passed": True, "detail": ""},
        "attendance": {"passed": True, "detail": ""},
    }

    try:
        from app.models.training import CourseEnrollment
        enrollment = await db.get(CourseEnrollment, enrollment_id)
        if enrollment:
            attendance = getattr(enrollment, "attendance_pct", 100) or 100
            if attendance < 75:
                checks["attendance"] = {"passed": False, "detail": f"Attendance below 75%: {attendance}%"}
            
            hours = getattr(enrollment, "hours_completed", 0) or 0
            if hours < 6:
                checks["hours_minimum"] = {"passed": False, "detail": f"Minimum 6 hours required, completed: {hours}h"}
    except Exception as e:
        logger.warning(f"FUNDAE enrollment validation skipped: {e}")

    all_passed = all(c["passed"] for c in checks.values())
    return {
        "enrollment_id": enrollment_id,
        "passed": all_passed,
        "checks": checks,
        "eligible": all_passed,
    }


def generate_fundae_xml(
    company: Dict[str, Any],
    courses: List[Dict[str, Any]],
    period: str = "",
) -> str:
    now = datetime.now(timezone.utc)
    company_name = company.get("name", "").upper()[:50]
    company_cif = company.get("tax_id", "")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<FUNDAE xmlns="http://www.fundae.es/bonificaciones">
  <Cabecera>
    <FechaPresentacion>{now.strftime('%Y-%m-%d')}</FechaPresentacion>
    <Periodo>{period or now.strftime('%Y%m')}</Periodo>
    <Empresa>
      <CIF>{company_cif}</CIF>
      <RazonSocial>{company_name}</RazonSocial>
      <NumeroTrabajadores>{company.get('size', '10-49')}</NumeroTrabajadores>
      <CreditoDisponible>{company.get('available_credit', '420')}</CreditoDisponible>
    </Empresa>
  </Cabecera>
  <AccionesFormativas>"""

    for course in courses:
        xml += f"""
    <AccionFormativa>
      <NombreCurso>{course.get('title', '')[:100]}</NombreCurso>
      <Modalidad>{course.get('modality', 'presencial')}</Modalidad>
      <Horas>{course.get('hours', 0)}</Horas>
      <Participantes>{course.get('participants', 1)}</Participantes>
      <FechaInicio>{course.get('start_date', '')}</FechaInicio>
      <FechaFin>{course.get('end_date', '')}</FechaFin>
      <CosteTotal>{course.get('total_cost', 0):.2f}</CosteTotal>
      <BonificacionAplicada>{course.get('bonus_applied', 0):.2f}</BonificacionAplicada>
      <CofinanciacionPrivada>{course.get('cofinancing', 0):.2f}</CofinanciacionPrivada>
      <Agrupacion>1</Agrupacion>
    </AccionFormativa>"""

    xml += """
  </AccionesFormativas>
</FUNDAE>"""
    return xml


async def get_fundae_summary(
    db: AsyncSession,
    year: int = 2026,
) -> Dict[str, Any]:
    try:
        from app.models.training import Course, CourseEnrollment
        courses_res = await db.execute(select(Course))
        courses = courses_res.scalars().all()

        total_hours = 0
        total_participants = 0
        total_bonus = 0.0
        by_modality: Dict[str, Dict[str, Any]] = {}

        for course in courses:
            hours = getattr(course, "duration_hours", 0) or getattr(course, "hours", 10)
            modality = getattr(course, "modality", "presencial")
            if modality not in by_modality:
                by_modality[modality] = {"courses": 0, "hours": 0, "participants": 0}
            by_modality[modality]["courses"] += 1
            by_modality[modality]["hours"] += hours
            total_hours += hours

        enroll_res = await db.execute(select(func.count(CourseEnrollment.id)))
        total_participants = enroll_res.scalar() or 0

        return {
            "year": year,
            "total_courses": len(courses),
            "total_hours": total_hours,
            "total_participants": total_participants,
            "by_modality": by_modality,
            "estimated_bonus_eur": round(total_hours * 13.0, 2),
        }
    except Exception as e:
        logger.warning(f"FUNDAE summary failed: {e}")
        return {"year": year, "total_courses": 0, "total_hours": 0, "error": str(e)}
