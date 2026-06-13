import smtplib
from email.message import EmailMessage
import os
from app.core.config import settings
from app.services.pdf_service import generate_executive_pdf
from sqlalchemy import select, func
from app.models.user import User
from app.models.scheduled_report import ScheduledReport
from app.core.database import engine, AsyncSessionGlobal
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from datetime import datetime

async def _get_report_data(tenant_id=None):
    if not tenant_id:
        return {"total": 0, "active": 0, "roles": []}

    tenant_schema = f"tenant_{tenant_id}"
    tenant_engine = engine.execution_options(schema_translate_map={None: tenant_schema})
    AsyncSessionTenant = async_sessionmaker(
        bind=tenant_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with AsyncSessionTenant() as db:
        # Aquí simplificamos consultando la tabla base User. 
        # En una app multi-tenant por schema, se debería configurar el search_path.
        total_result = await db.execute(select(func.count()).select_from(User))
        total = total_result.scalar() or 0

        active_result = await db.execute(select(func.count()).select_from(User).where(User.is_active == True))
        active = active_result.scalar() or 0

        roles_result = await db.execute(
            select(User.role, func.count(User.id)).group_by(User.role)
        )
        roles = [
            {"name": r.title(), "count": c, "percentage": round(c / total * 100, 1) if total > 0 else 0}
            for r, c in roles_result.all()
        ]
        return {"total": total, "active": active, "roles": roles}

def send_email_with_pdf(to_email: str, pdf_bytes: bytes, tenant_name: str):
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        print(f"[{datetime.now()}] SIMULACIÓN: Enviando reporte a {to_email} para {tenant_name}")
        return

    msg = EmailMessage()
    msg['Subject'] = f'Reporte Ejecutivo HR - {tenant_name}'
    msg['From'] = settings.EMAILS_FROM_EMAIL or settings.SMTP_USER
    msg['To'] = to_email
    msg.set_content(f"Adjunto encontrarás el reporte ejecutivo HR para {tenant_name}.")

    msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename='executive_report.pdf')

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        print(f"[{datetime.now()}] Email enviado correctamente a {to_email}")
    except Exception as e:
        print(f"[{datetime.now()}] Error enviando email a {to_email}: {e}")

async def send_scheduled_report(email_to: str, tenant_id: str):
    print(f"Iniciando generación de reporte para {email_to}")
    
    stats = await _get_report_data(tenant_id)
    
    tenant_name = tenant_id or "Acme Corp"
    pdf_bytes = generate_executive_pdf(tenant_name=f"Data for {tenant_name}", stats=stats)
    
    send_email_with_pdf(email_to, pdf_bytes, tenant_name)
    return f"Reporte enviado a {email_to}"

async def process_all_scheduled_reports():
    """Tarea que lee la base de datos y lanza los reportes agendados."""
    async with AsyncSessionGlobal() as db:
        result = await db.execute(select(ScheduledReport).where(ScheduledReport.is_active == True))
        schedules = result.scalars().all()
            
    # Simplificación: Lanzar todos sin importar la frecuencia (para la demo)
    # En producción habría lógica para verificar si ya toca según la frecuencia y el last_run_at
    for schedule in schedules:
        await send_scheduled_report(schedule.email_to, schedule.tenant_id)
        
    return f"Procesados {len(schedules)} schedules activos"
