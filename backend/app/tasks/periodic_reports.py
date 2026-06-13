from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.logger import logger
from app.services.pdf_service import generate_executive_pdf
from app.services.courier_service import send_email_with_attachment

# Engine sincrónico al schema general (public)
sync_global_uri = settings.SYNC_DATABASE_URI
sync_engine = create_engine(sync_global_uri)
SessionLocal = sessionmaker(bind=sync_engine)

def send_monthly_reports():
    """
    Tarea Periódica.
    Por cada Tenant existente:
    1. Calcula sus métricas y renderiza su reporte Ejecutivo PDF en WeasyPrint.
    2. Usa Courier para enviarle el reporte PDF adjunto a su HR Admin.
    """
    logger.info("Iniciando batch process de Reportes Mensuales para todos los Tenants.")
    
    with SessionLocal() as session:
        # 1. Obtener lista de todos los tenants registrados
        # Asumiendo que el modelo Tenant está en el esquema `public`
        try:
            result = session.execute(text("SELECT id, name FROM public.tenants WHERE is_active = true"))
            tenants = result.fetchall()
        except Exception as e:
            logger.error(f"Error consultando tenants: {e}")
            return "Error al consultar tenants"
        
        if not tenants:
            logger.info("No hay tenants activos para enviar reportes.")
            return "No tenants"
            
        # 2. Iterar sobre todos los esquemas
        for tenant_id, tenant_name in tenants:
            logger.info(f"Procesando reporte mensual para tenant: {tenant_name} ({tenant_id})")
            
            try:
                # 3. Conectarse dinámicamente al esquema de este tenant
                tenant_schema = f"tenant_{tenant_id}"
                tenant_engine = sync_engine.execution_options(schema_translate_map={None: tenant_schema})
                
                with tenant_engine.begin() as tenant_conn:
                    # Encontrar admin email
                    admin_res = tenant_conn.execute(text("SELECT email FROM users WHERE role = 'hr_admin' LIMIT 1"))
                    admin_email = admin_res.scalar()
                    
                    if not admin_email:
                        logger.warning(f"Tenant {tenant_name} no tiene hr_admin. Omitiendo.")
                        continue
                
                    # Traer métricas básicas
                    total_res = tenant_conn.execute(text("SELECT count(*) FROM users"))
                    total_users = total_res.scalar() or 0
                    
                    active_res = tenant_conn.execute(text("SELECT count(*) FROM users WHERE is_active = true"))
                    active_users = active_res.scalar() or 0
                    
                    roles_res = tenant_conn.execute(text("SELECT role, count(id) FROM users GROUP BY role"))
                    roles_summary = []
                    for role_name, count in roles_res.fetchall():
                        roles_summary.append({
                            "name": str(role_name).title(),
                            "count": count,
                            "percentage": round((count / total_users * 100), 1) if total_users > 0 else 0
                        })
                
                stats = {
                    "total": total_users,
                    "active": active_users,
                    "roles": roles_summary
                }
                
                # 4. Generar el binario PDF en background
                pdf_bytes = generate_executive_pdf(tenant_name=tenant_name, stats=stats)
                
                # 5. Enviar usando Courier API
                body_msg = f"Hola, {tenant_name}.\n\nAdjunto encontrarás el reporte consolidado de Empleados del último mes."
                filename = f"Reporte_Mensual_SuccessCore_{tenant_id}.pdf"
                
                send_email_with_attachment(
                    to_email=admin_email,
                    subject=f"Reporte Ejecutivo Mensual - {tenant_name}",
                    body=body_msg,
                    attachment_bytes=pdf_bytes,
                    filename=filename
                )
                
            except Exception as e:
                logger.error(f"Fallo al distribuir informe al tenant {tenant_id}: {e}")
                
    return "Reporte mensual distribuido a todos los tenants"
