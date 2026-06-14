from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from sqlalchemy.orm import selectinload
from typing import List, Optional
from pydantic import BaseModel
import uuid
import json
from datetime import datetime, timezone

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.dependencies import get_tenant_db, get_global_db, require_roles, require_super_admin, get_current_user
from app.api.v1._pagination import paginate_query
from app.schemas.pagination import PaginatedResponse
from app.models.tenant import Tenant
from app.models.user import User
from app.models.training import Course, CourseEnrollment
from app.models.calendar import Task
from app.models.admin import AuditLog
from app.models.rbac import Role, Permission, RolePermission
from app.schemas.admin import (
    AuditLogResponse, TenantModulesUpdate, CourseAssignmentCreate,
    TaskAssignmentCreate, UserRoleUpdate
)
from app.services.tenant_provisioning import provision_tenant, deprovision_tenant
from app.services.db_backup import backup_database, list_backups, verify_backup
from app.services.data_export import export_employee_data
from app.services.data_erasure import erase_user_data
from app.services.retention import enforce_retention, configure_retention
from app.services.cross_tenant_analytics import get_platform_analytics
from app.services.webhook_replay import replay_delivery
from app.services.webhook_engine import get_webhook_engine
from app.services.dashboard_summary import get_admin_dashboard_summary
from app.services.csv_export import export_all_employees_csv
from app.services.gdpr_export import build_gdpr_export_package
from app.services.audit_archive import archive_old_audit_logs
from app.services.residency_audit import get_data_residency_proof
from app.services.connector_templates import list_connectors, get_connector_config
from app.services.email_digest_sender import send_daily_digest
from app.services.audit_search import search_audit_logs
from app.services.doc_templates import TEMPLATES, generate_pdf
from app.services.storage_usage import get_tenant_storage_usage
from app.core.logger import logger

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


def _get_user_id(user_payload: dict) -> str:
    """
    [H2 FIX] Extract the actual user ID from the JWT payload.
    The standard field is 'sub', not 'user_id'.
    """
    sub = user_payload.get("sub", "")
    if "|" in sub:
        return sub.split("|")[-1]
    return sub or "unknown"


# Helper function to create an audit log
async def create_audit_log(
    db: AsyncSession,
    user_id: str,
    action: str,
    details: str,
    request: Request
):
    ip_address = request.client.host if request.client else "unknown"
    audit = AuditLog(
        id=uuid.uuid4().hex,
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip_address
    )
    db.add(audit)
    # [M10 FIX] Use flush() instead of commit() so the caller controls the transaction.
    # Committing here can cause double-commits or leave the log orphaned.
    await db.flush()

# ==========================================
# AUDIT LOGS ENDPOINT
# ==========================================
@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """Obtener el historial completo de auditoría del inquilino."""
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()))
    return result.scalars().all()

# ==========================================
# MODULE MARKETPLACE TOGGLES
# ==========================================
@router.post("/modules/toggle")
async def toggle_tenant_modules(
    modules_in: TenantModulesUpdate,
    request: Request,
    global_db: AsyncSession = Depends(get_global_db),
    tenant_db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(require_super_admin())
):
    """
    Activar o desactivar módulos del inquilino a nivel global en la base de datos pública.
    Requiere permisos de Super Administrador.
    """
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id") or current_user.get("tenant_id") or "acme_corp"
    user_id = _get_user_id(current_user)  # [H2 FIX]

    # Obtener inquilino
    result = await global_db.execute(
        select(Tenant).where(
            (Tenant.id == tenant_id) | (Tenant.schema_name == f"tenant_{tenant_id}")
        )
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Inquilino no encontrado")

    # Modificar módulos
    tenant.enabled_modules = modules_in.enabled_modules
    await global_db.commit()

    # Registrar en logs de auditoría (tenant_db)
    details = f"Modificado estado de módulos: {json.dumps(modules_in.enabled_modules)}"
    await create_audit_log(tenant_db, user_id, "MODULE_TOGGLE", details, request)

    return {"message": "Configuración de módulos de la plataforma guardada con éxito."}

@router.get("/modules")
async def get_tenant_modules(
    global_db: AsyncSession = Depends(get_global_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtener la lista de modulos activos para el tenant actual.
    Cualquier usuario logeado puede ver esto para renderizar su UI.
    """
    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id") or current_user.get("tenant_id") or "acme_corp"

    result = await global_db.execute(
        select(Tenant).where(
            (Tenant.id == tenant_id) | (Tenant.schema_name == f"tenant_{tenant_id}")
        )
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Inquilino no encontrado")

    return {"enabled_modules": tenant.enabled_modules or {}}

# ==========================================
# RBAC - GLOBAL ROLE BUILDER
# ==========================================
from pydantic import BaseModel
class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: List[str] # List of permission IDs

@router.get("/permissions")
async def list_permissions(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "admin"]))
):
    result = await db.execute(select(Permission).order_by(Permission.module))
    return result.scalars().all()

@router.get("/roles")
async def list_roles(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "admin"]))
):
    result = await db.execute(
        select(Role).options(
            selectinload(Role.permissions).selectinload(RolePermission.permission)
        )
    )
    roles = result.scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "is_system_default": r.is_system_default,
            "permissions": [rp.permission.id for rp in r.permissions]
        }
        for r in roles
    ]

@router.post("/roles")
async def create_role(
    role_in: RoleCreate,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "admin"]))
):
    new_role = Role(id=uuid.uuid4().hex, name=role_in.name, description=role_in.description)
    db.add(new_role)
    await db.flush()

    for perm_id in role_in.permissions:
        rp = RolePermission(id=uuid.uuid4().hex, role_id=new_role.id, permission_id=perm_id)
        db.add(rp)
    
    await db.commit()
    await create_audit_log(db, _get_user_id(current_user), "ROLE_CREATED", f"Rol creado: {role_in.name}", request)  # [H2 FIX]
    return {"message": "Rol creado con exito", "id": new_role.id}

@router.put("/roles/{role_id}")
async def update_role(
    role_id: str,
    role_in: RoleCreate,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "admin"]))
):
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
        
    role.name = role_in.name
    role.description = role_in.description
    
    # Eliminar permisos antiguos
    await db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    
    # Insertar nuevos permisos
    for perm_id in role_in.permissions:
        rp = RolePermission(id=uuid.uuid4().hex, role_id=role_id, permission_id=perm_id)
        db.add(rp)
        
    await db.commit()
    await create_audit_log(db, _get_user_id(current_user), "ROLE_UPDATED", f"Rol actualizado: {role_in.name}", request)  # [H2 FIX]
    return {"message": "Rol actualizado con exito"}

@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "admin"]))
):
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
        
    if role.is_system_default:
        raise HTTPException(status_code=400, detail="No se puede eliminar un rol del sistema por defecto")
        
    await db.delete(role)
    await db.commit()
    await create_audit_log(db, _get_user_id(current_user), "ROLE_DELETED", f"Rol eliminado: {role.name}", request)  # [H2 FIX]
    return {"message": "Rol eliminado con exito"}


# ==========================================
# ASSIGNMENTS HUB (COURSES & TASKS)
# ==========================================
@router.post("/assignments/courses", status_code=status.HTTP_201_CREATED)
async def assign_course_to_users(
    assign_in: CourseAssignmentCreate,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin"]))
):
    """Asignar un curso a múltiples empleados en lote (LMS)."""
    user_id = _get_user_id(user_payload)  # [H2 FIX]
    
    # Validar que el curso exista
    course_res = await db.execute(select(Course).where(Course.id == assign_in.course_id))
    course = course_res.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    assigned_count = 0
    for uid in assign_in.user_ids:
        # Verificar que el usuario exista
        user_res = await db.execute(select(User).where(User.id == uid))
        user = user_res.scalar_one_or_none()
        if not user:
            continue

        # Verificar si ya tiene matrícula
        enroll_res = await db.execute(
            select(CourseEnrollment).where(
                CourseEnrollment.user_id == uid,
                CourseEnrollment.course_id == assign_in.course_id
            )
        )
        existing = enroll_res.scalar_one_or_none()
        if existing:
            continue

        # Crear nueva matrícula/asignación
        enroll = CourseEnrollment(
            id=uuid.uuid4().hex,
            user_id=uid,
            course_id=assign_in.course_id,
            status="assigned",
            progress_percentage=0.0,
            time_spent_seconds=0
        )
        db.add(enroll)
        assigned_count += 1

    await db.commit()

    details = f"Asignado curso '{course.title}' a {assigned_count} empleados."
    await create_audit_log(db, user_id, "COURSE_ASSIGNED", details, request)

    return {"message": f"Curso asignado correctamente a {assigned_count} empleados."}


@router.post("/assignments/tasks", status_code=status.HTTP_201_CREATED)
async def assign_tasks_to_users(
    assign_in: TaskAssignmentCreate,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin"]))
):
    """Asignar una tarea personalizada en lote a múltiples empleados."""
    user_id = _get_user_id(user_payload)  # [H2 FIX]
    assigned_count = 0

    for uid in assign_in.user_ids:
        # Verificar usuario
        user_res = await db.execute(select(User).where(User.id == uid))
        if not user_res.scalar_one_or_none():
            continue

        # Crear tarea de calendario
        task = Task(
            id=uuid.uuid4().hex,
            title=assign_in.title,
            description=assign_in.description,
            assigned_to=uid,
            created_by=user_id,
            due_date=assign_in.due_date,
            priority=assign_in.priority,
            status="todo"
        )
        db.add(task)
        assigned_count += 1

    await db.commit()

    details = f"Creada y asignada tarea '{assign_in.title}' a {assigned_count} empleados."
    await create_audit_log(db, user_id, "TASK_ASSIGNED", details, request)

    return {"message": f"Tarea asignada correctamente a {assigned_count} empleados."}


@router.get("/assignments/status")
async def get_assignments_status(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """Obtener el listado detallado de todas las asignaciones de cursos y tareas activas."""
    # Matrículas formativas
    enroll_query = select(CourseEnrollment, Course.title, User.full_name).join(
        Course, Course.id == CourseEnrollment.course_id
    ).join(
        User, User.id == CourseEnrollment.user_id
    )
    enroll_res = await db.execute(enroll_query)
    enrollments_data = enroll_res.all()

    # Tareas de empleados
    task_query = select(Task, User.full_name).join(
        User, User.id == Task.assigned_to
    )
    task_res = await db.execute(task_query)
    tasks_data = task_res.all()

    return {
        "courses": [
            {
                "enrollment_id": row[0].id,
                "course_id": row[0].course_id,
                "course_title": row[1],
                "employee_name": row[2],
                "status": row[0].status,
                "progress": float(row[0].progress_percentage),
                "score": float(row[0].score) if row[0].score else None,
                "assigned_at": row[0].created_at.isoformat()
            } for row in enrollments_data
        ],
        "tasks": [
            {
                "task_id": row[0].id,
                "title": row[0].title,
                "description": row[0].description,
                "employee_name": row[1],
                "priority": row[0].priority,
                "status": row[0].status,
                "due_date": row[0].due_date.isoformat() if row[0].due_date else None,
                "created_at": row[0].created_at.isoformat()
            } for row in tasks_data
        ]
    }

# ==========================================
# ROLE MANAGEMENT & DIRECTORY
# ==========================================
@router.get("/users")
async def list_tenant_users(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """Listado del directorio de usuarios para la asignación de roles y accesos."""
    result = await db.execute(select(User).order_by(User.full_name.asc()))
    return result.scalars().all()


@router.post("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role_in: UserRoleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    user_payload: dict = Depends(require_roles(["hr_admin"]))
):
    """Modificar directamente el rol de acceso de un empleado en la organización."""
    admin_id = _get_user_id(user_payload)  # [H2 FIX]

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    old_role = user.role
    user.role = role_in.role
    await db.commit()

    details = f"Cambiado rol del usuario {user.email} de '{old_role}' a '{role_in.role}'."
    await create_audit_log(db, admin_id, "ROLE_CHANGED", details, request)

    return {"message": f"Rol de {user.full_name} actualizado correctamente a '{role_in.role}'."}


# ==========================================
# TENANT PROVISIONING (Super Admin only)
# ==========================================

class TenantProvisionRequest(BaseModel):
    name: str
    schema_name: str
    admin_email: str
    admin_password: str
    admin_name: str
    tier: str = "FREE"


class TenantDeprovisionRequest(BaseModel):
    confirmation: str


@router.post("/tenants", status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_tenant(
    body: TenantProvisionRequest,
    request: Request,
    global_db: AsyncSession = Depends(get_global_db),
    tenant_db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(require_super_admin()),
):
    try:
        result = await provision_tenant(
            name=body.name,
            schema_name=body.schema_name,
            admin_email=body.admin_email,
            admin_password=body.admin_password,
            admin_name=body.admin_name,
            tier=body.tier,
        )
        await create_audit_log(tenant_db, _get_user_id(current_user), "TENANT_CREATED",
            f"Created tenant {body.name} (schema: {body.schema_name}, tier: {body.tier})", request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Tenant provisioning failed: {e}")
        raise HTTPException(status_code=500, detail=f"Provisioning failed: {str(e)}")


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    body: TenantDeprovisionRequest,
    request: Request,
    hard: bool = Query(False),
    global_db: AsyncSession = Depends(get_global_db),
    tenant_db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(require_super_admin()),
):
    if hard and body.confirmation != f"DELETE {tenant_id}":
        raise HTTPException(status_code=400, detail="Confirmation text must be 'DELETE {tenant_id}' for hard delete")

    try:
        result = await deprovision_tenant(tenant_id, hard=hard)
        await create_audit_log(tenant_db, _get_user_id(current_user), "TENANT_DELETED",
            f"{'Hard' if hard else 'Soft'} deprovisioned tenant {result['tenant_name']} ({tenant_id})", request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/tenants/{tenant_id}/status")
@limiter.limit("20/minute")
async def get_tenant_status(
    tenant_id: str,
    global_db: AsyncSession = Depends(get_global_db),
    _: bool = Depends(require_super_admin()),
):
    result = await global_db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {
        "id": tenant.id,
        "name": tenant.name,
        "schema_name": tenant.schema_name,
        "tier": tenant.tier,
        "is_active": tenant.is_active,
        "created_at": tenant.created_at.isoformat(),
    }


@router.post("/backup")
async def trigger_backup(
    _: bool = Depends(require_super_admin()),
):
    try:
        from app.core.config import settings
        filepath = backup_database(settings.SYNC_DATABASE_URI)
        return {"status": "success", "path": filepath}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")


@router.get("/backups")
async def get_backups(
    _: bool = Depends(require_super_admin()),
):
    return {"backups": list_backups()}


@router.post("/backup/verify")
async def verify_backup_integrity(
    body: dict,
    _: bool = Depends(require_super_admin()),
):
    filepath = body.get("filepath", "")
    if not filepath:
        raise HTTPException(status_code=400, detail="filepath is required")
    return verify_backup(filepath)


@router.post("/cleanup-orphans")
async def cleanup_orphan_data(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from sqlalchemy import text as sa_text
    cleaned = {}
    tables = ["notifications", "kudos", "vacation_requests", "expense_claims", "time_logs",
              "course_enrollments", "chat_messages", "employee_history"]
    for table in tables:
        try:
            result = await db.execute(sa_text(f"DELETE FROM {table} WHERE user_id NOT IN (SELECT id FROM users)"))
            cleaned[table] = result.rowcount
        except Exception:
            cleaned[table] = 0
    await db.commit()
    return {"cleaned_tables": cleaned, "total_removed": sum(cleaned.values())}


@router.post("/send-digest")
async def send_email_digest(
    body: dict,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    admin_email = body.get("email", "")
    if not admin_email:
        raise HTTPException(status_code=400, detail="email is required")
    return await send_daily_digest(db, admin_email)


@router.get("/audit-logs/search")
async def search_audit_logs_endpoint(
    q: str = Query(""),
    user_id: str = Query(None),
    action: str = Query(None),
    from_date: str = Query(None),
    to_date: str = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return await search_audit_logs(db, q, user_id, action, from_date, to_date, limit)


@router.get("/document-templates")
async def list_doc_templates(
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return {"templates": [{"id": k, "name": v["name"], "fields": v["fields"]} for k, v in TEMPLATES.items()]}


@router.post("/document-templates/{template_name}/generate")
async def generate_document(
    template_name: str,
    data: dict,
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from fastapi.responses import Response
    try:
        pdf_bytes = generate_pdf(template_name, data)
        return Response(content=pdf_bytes, media_type="application/pdf",
                        headers={"Content-Disposition": f"attachment; filename={template_name}.pdf"})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/audit-logs/stream")
async def stream_audit_logs(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    from fastapi.responses import StreamingResponse
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(500))
    logs = result.scalars().all()

    async def generate():
        for log in logs:
            entry = {
                "timestamp": log.created_at.isoformat(),
                "user_id": log.user_id,
                "action": log.action,
                "details": log.details,
                "ip_address": log.ip_address,
            }
            yield json.dumps(entry, default=str) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson", headers={
        "Content-Disposition": "attachment; filename=audit_logs.ndjson"
    })


@router.get("/employees/{user_id}/export")
async def export_employee_archive(
    user_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    from fastapi.responses import Response
    try:
        zip_bytes = await export_employee_data(db, user_id)
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=employee_{user_id}_export.zip"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/employees/{user_id}/erase")
async def erase_employee_data(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(require_super_admin()),
):
    try:
        result = await erase_user_data(db, user_id)
        await create_audit_log(db, _get_user_id(current_user), "GDPR_ERASURE",
            f"Right-to-erasure executed for user {result['original_email']} ({user_id})", request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/retention/enforce")
async def enforce_data_retention(
    request: Request,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(require_super_admin()),
):
    result = await enforce_retention(db)
    await create_audit_log(db, _get_user_id(current_user), "RETENTION_ENFORCED",
        f"Data retention policy applied: {result['rules_applied']} rules", request)
    return result


@router.put("/retention/{table_name}")
async def update_retention_rule(
    table_name: str,
    body: dict,
    db: AsyncSession = Depends(get_tenant_db),
    _: bool = Depends(require_super_admin()),
):
    days = body.get("days", 365)
    configure_retention(table_name, days)
    return {"status": "updated", "table": table_name, "retention_days": days}


@router.post("/backup/restore")
async def restore_backup(
    body: dict,
    _: bool = Depends(require_super_admin()),
):
    import subprocess, os
    filepath = body.get("filepath", "")
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=400, detail="Backup file not found")

    try:
        from app.core.config import settings
        target_url = settings.SYNC_DATABASE_URI or settings.SQLALCHEMY_DATABASE_URI
        result = subprocess.run(
            ["psql", target_url, "-f", filepath],
            shell=False, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr[:500])
        return {"status": "restored", "file": filepath}
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="psql not found in PATH")


@router.get("/platform-analytics")
async def get_platform_analytics_endpoint(
    global_db: AsyncSession = Depends(get_global_db),
    _: bool = Depends(require_super_admin()),
):
    return await get_platform_analytics(global_db)


@router.get("/reseller-keys")
async def get_reseller_keys_status(
    _: bool = Depends(require_super_admin()),
):
    from app.core.config import settings
    return {
        "keys": {
            "openai": {"configured": bool(settings.OPENAI_API_KEY), "prefix": settings.OPENAI_API_KEY[:12] + "..." if settings.OPENAI_API_KEY else "not set"},
            "gemini": {"configured": bool(settings.GEMINI_API_KEY), "prefix": settings.GEMINI_API_KEY[:12] + "..." if settings.GEMINI_API_KEY else "not set"},
            "openrouter": {"configured": bool(settings.OPENROUTER_API_KEY), "prefix": settings.OPENROUTER_API_KEY[:12] + "..." if settings.OPENROUTER_API_KEY else "not set"},
            "anthropic": {"configured": bool(settings.ANTHROPIC_API_KEY), "prefix": settings.ANTHROPIC_API_KEY[:12] + "..." if settings.ANTHROPIC_API_KEY else "not set"},
            "xai": {"configured": bool(settings.GROK_API_KEY), "prefix": settings.GROK_API_KEY[:12] + "..." if settings.GROK_API_KEY else "not set"},
        },
        "encryption_key_configured": bool(settings.ENCRYPTION_KEY),
        "mode": "reseller" if settings.OPENAI_API_KEY else "byok_only"
    }


@router.get("/dashboard-summary")
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return await get_admin_dashboard_summary(db)


@router.get("/employees/export-csv")
async def export_employees_csv(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    from fastapi.responses import PlainTextResponse
    csv_data = await export_all_employees_csv(db)
    return PlainTextResponse(csv_data, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=employees_export.csv"})


@router.get("/employees/{user_id}/gdpr-export")
async def gdpr_employee_export(
    user_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from fastapi.responses import Response
    try:
        zip_bytes = await build_gdpr_export_package(db, user_id)
        return Response(content=zip_bytes, media_type="application/zip",
                        headers={"Content-Disposition": f"attachment; filename=gdpr_export_{user_id}.zip"})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/webhooks/{subscription_id}/replay/{delivery_id}")
async def replay_webhook(
    subscription_id: str,
    delivery_id: str,
    _: bool = Depends(require_super_admin()),
):
    try:
        engine = get_webhook_engine()
        result = await replay_delivery(subscription_id, delivery_id, engine)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/webhooks/{subscription_id}/deliveries")
async def get_webhook_deliveries(
    subscription_id: str,
    limit: int = 50,
    _: bool = Depends(require_super_admin()),
):
    engine = get_webhook_engine()
    logs = await engine.get_delivery_logs(subscription_id, limit)
    return {"subscription_id": subscription_id, "deliveries": logs}


@router.post("/audit-logs/archive")
async def archive_audit_logs_endpoint(
    retention_days: int = Query(365),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return await archive_old_audit_logs(db, retention_days)


@router.get("/data-residency-audit")
async def data_residency_audit(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.services.data_residency import get_tenant_residency
    residency = await get_tenant_residency(db, "acme_corp")
    return get_data_residency_proof("acme_corp", residency)


@router.get("/connectors")
async def get_connectors(
    _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    return {"connectors": list_connectors()}


@router.get("/connectors/{provider}")
async def get_connector_detail(
    provider: str,
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    config = get_connector_config(provider)
    if not config:
        raise HTTPException(status_code=404, detail="Provider not found")
    return config


@router.get("/tenant-usage-report")
async def get_tenant_usage_report(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from datetime import datetime, timezone
    from app.models.agent import AgentExecutionRun
    from sqlalchemy import func
    from app.services.api_analytics import get_analytics
    from app.services.dept_usage import get_dept_usage_stats

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_runs = await db.execute(select(func.count(AgentExecutionRun.id)).where(AgentExecutionRun.created_at >= month_start))
    total_cost = await db.execute(select(func.coalesce(func.sum(AgentExecutionRun.cost_usd), 0)).where(AgentExecutionRun.created_at >= month_start))
    success_runs = await db.execute(select(func.count(AgentExecutionRun.id)).where(AgentExecutionRun.created_at >= month_start, AgentExecutionRun.status == "success"))
    analytics = get_analytics()
    dept = get_dept_usage_stats()

    return {
        "period": f"{month_start.strftime('%Y-%m')} to {now.strftime('%Y-%m-%d')}",
        "ai_agents": {"total_runs": total_runs.scalar() or 0, "success_rate": round((success_runs.scalar() or 0) / max(total_runs.scalar() or 1, 1) * 100, 1), "total_cost_usd": round(total_cost.scalar() or 0, 4)},
        "api_usage": {"total_requests": analytics.get("total_requests", 0), "unique_clients": analytics.get("unique_clients", 0), "top_routes": analytics.get("routes", [])[:5]},
        "dept_usage": dept,
    }


@router.post("/users/bulk-status")
async def bulk_user_status(
    body: dict,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.models.user import User
    user_ids = body.get("user_ids", [])
    is_active = body.get("is_active", True)
    if not user_ids:
        raise HTTPException(status_code=400, detail="user_ids is required")
    await db.execute(update(User).where(User.id.in_(user_ids)).values(is_active=is_active))
    await db.commit()
    return {"updated": len(user_ids), "is_active": is_active}


@router.get("/storage-usage")
async def get_storage_usage(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return await get_tenant_storage_usage(db)
