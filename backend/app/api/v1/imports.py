"""
imports.py — Endpoints de carga masiva de empleados.
Redis-backed task queue with persistent status tracking.
"""

import os
import shutil
import uuid
import io
import csv

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from fastapi.responses import StreamingResponse

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.dependencies import require_roles, get_current_user, get_tenant_db
from app.core.task_queue import enqueue, get_task_status, register_task
from app.tasks.employee_sync import process_employees_file
from app.services.import_preview import preview_import
from sqlalchemy.ext.asyncio import AsyncSession

import asyncio

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

UPLOAD_DIR        = "downloads/imports"
MAX_UPLOAD_SIZE_MB = 50
MAX_UPLOAD_BYTES   = MAX_UPLOAD_SIZE_MB * 1024 * 1024

os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
ALLOWED_MIME_TYPES  = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
}


async def _import_employees(task_id: str, file_path: str, tenant_id: str, progress_callback=None):
    """Async wrapper for process_employees_file to work with task queue."""
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        process_employees_file,
        file_path,
        tenant_id,
        progress_callback
    )
    return result


async def _import_candidates(task_id: str, file_path: str, tenant_id: str, progress_callback=None):
    from app.tasks.employee_sync import process_candidates_file
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        process_candidates_file,
        file_path,
        tenant_id,
        progress_callback
    )
    return result


async def _import_courses(task_id: str, file_path: str, tenant_id: str, progress_callback=None):
    from app.tasks.employee_sync import process_courses_file
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        process_courses_file,
        file_path,
        tenant_id,
        progress_callback
    )
    return result


async def _import_expenses(task_id: str, file_path: str, tenant_id: str, progress_callback=None):
    from app.tasks.employee_sync import process_expenses_file
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        process_expenses_file,
        file_path,
        tenant_id,
        progress_callback
    )
    return result


# Register all tasks with the queue
register_task("import_employees", _import_employees)
register_task("import_candidates", _import_candidates)
register_task("import_courses", _import_courses)
register_task("import_expenses", _import_expenses)


@limiter.limit("5/minute")
@router.post("/upload")
async def upload_employees_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"])),
):
    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Extension no permitida: '{ext}'. Use .csv o .xlsx.")

    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=415, detail=f"MIME type no permitido: '{file.content_type}'.")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Archivo demasiado grande. Maximo {MAX_UPLOAD_SIZE_MB} MB.")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="El archivo esta vacio.")

    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id    = app_metadata.get("tenant_id") or current_user.get("tenant_id") or "acme_corp"

    task_id       = uuid.uuid4().hex
    safe_filename = f"{tenant_id}_{task_id}{ext}"
    file_path     = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buf:
        buf.write(content)

    import logging
    _logger = logging.getLogger("successcore.imports")
    try:
        await enqueue(
            "import_employees",
            args={"file_path": file_path, "tenant_id": tenant_id},
            tenant_id=tenant_id,
        )
    except Exception as e:
        _logger.error(f"Redis enqueue failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="El servicio de tareas en segundo plano no esta disponible. Intenta de nuevo en unos minutos."
        )

    return {
        "status":    "queued",
        "message":   "Carga masiva encolada correctamente.",
        "task_id":   task_id,
        "filename":  file.filename,
        "size_kb":   round(len(content) / 1024, 1),
    }


@router.get("/status/{task_id}")
async def get_import_status(
    task_id: str,
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"])),
):
    status = await get_task_status(task_id)
    if status.get("status") == "not_found":
        return {"state": "FAILURE", "info": "Tarea no encontrada."}
    return {
        "state": status.get("status", "unknown"),
        "progress": status.get("progress", 0),
        "inserted": status.get("inserted", 0),
        "duplicates": status.get("duplicates", 0),
        "rejected": status.get("rejected", 0),
        "row_errors": status.get("row_errors", []),
        "error": status.get("error"),
    }


ENTITY_DEFINITIONS = [
    {
        "type": "employees",
        "label": "Employees",
        "description": "Import employee records",
        "required_columns": ["email", "full_name"],
        "optional_columns": ["department", "role", "phone", "hire_date", "manager_email"],
        "template_url": "/imports/template?entity=employees"
    },
    {
        "type": "candidates",
        "label": "Candidates",
        "description": "Import job candidates",
        "required_columns": ["email", "first_name", "last_name", "job_id"],
        "optional_columns": ["phone", "stage", "source", "linkedin_url"],
        "template_url": "/imports/template?entity=candidates"
    },
    {
        "type": "courses",
        "label": "Training Courses",
        "description": "Import course catalog entries",
        "required_columns": ["title"],
        "optional_columns": ["description", "is_scorm", "scorm_version", "package_url", "min_duration_hours", "is_fundae_eligible", "category"],
        "template_url": "/imports/template?entity=courses"
    },
    {
        "type": "expenses",
        "label": "Expense Claims",
        "description": "Import expense records",
        "required_columns": ["merchant", "date", "total_amount"],
        "optional_columns": ["category", "tax_amount", "status", "description"],
        "template_url": "/imports/template?entity=expenses"
    }
]

TEMPLATE_ROWS = {
    "employees": {
        "headers": ["email", "full_name", "department", "role"],
        "example": ["ana.garcia@empresa.com", "Ana Garcia", "Recursos Humanos", "hr_admin"],
    },
    "candidates": {
        "headers": ["email", "first_name", "last_name", "job_id", "stage", "source"],
        "example": ["juan.perez@email.com", "Juan", "Perez", "abc123job", "applied", "LinkedIn"],
    },
    "courses": {
        "headers": ["title", "description", "is_scorm", "min_duration_hours"],
        "example": ["Leadership 101", "Intro to leadership skills", "false", "4"],
    },
    "expenses": {
        "headers": ["merchant", "date", "total_amount", "category", "description"],
        "example": ["Starbucks", "2025-01-15", "25.50", "meals", "Client lunch"],
    },
}


@router.get("/entities")
async def get_import_entities():
    """Return available entity types for import with their required/optional columns"""
    return {"entities": ENTITY_DEFINITIONS}


@limiter.limit("5/minute")
@router.post("/upload/{entity_type}")
async def upload_entity_file(
    request: Request,
    entity_type: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"])),
):
    if entity_type not in {e["type"] for e in ENTITY_DEFINITIONS}:
        raise HTTPException(status_code=400, detail=f"Unknown entity type: {entity_type}")

    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Extension no permitida: '{ext}'. Use .csv o .xlsx.")

    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=415, detail=f"MIME type no permitido: '{file.content_type}'.")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Archivo demasiado grande. Maximo {MAX_UPLOAD_SIZE_MB} MB.")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="El archivo esta vacio.")

    app_metadata = current_user.get("https://successcore.com/app_metadata", {})
    tenant_id = app_metadata.get("tenant_id") or current_user.get("tenant_id") or "acme_corp"

    task_id = uuid.uuid4().hex
    safe_filename = f"{tenant_id}_{task_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buf:
        buf.write(content)

    task_map = {
        "employees": "import_employees",
        "candidates": "import_candidates",
        "courses": "import_courses",
        "expenses": "import_expenses",
    }
    task_name = task_map[entity_type]

    import logging
    _logger = logging.getLogger("successcore.imports")
    try:
        await enqueue(
            task_name,
            args={"file_path": file_path, "tenant_id": tenant_id},
            tenant_id=tenant_id,
        )
    except Exception as e:
        _logger.error(f"Redis enqueue failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="El servicio de tareas en segundo plano no esta disponible. Intenta de nuevo en unos minutos."
        )

    return {
        "status": "queued",
        "message": "Carga masiva encolada correctamente.",
        "task_id": task_id,
        "filename": file.filename,
        "size_kb": round(len(content) / 1024, 1),
        "entity_type": entity_type,
    }


@router.get("/template/{entity_type}")
async def download_template(entity_type: str):
    """Generate a CSV template with headers for the given entity type"""
    tmpl = TEMPLATE_ROWS.get(entity_type)
    if not tmpl:
        raise HTTPException(status_code=400, detail=f"No template for entity: {entity_type}")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(tmpl["headers"])
    writer.writerow(tmpl["example"])
    output.seek(0)

    filename_map = {
        "employees": "plantilla_empleados.csv",
        "candidates": "plantilla_candidatos.csv",
        "courses": "plantilla_cursos.csv",
        "expenses": "plantilla_gastos.csv",
    }

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename_map.get(entity_type, 'plantilla.csv')}"},
    )


@router.get("/template")
async def download_template():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["email", "full_name", "department", "role"])
    writer.writerow(["ana.garcia@empresa.com",  "Ana Garcia",    "Recursos Humanos", "hr_admin"])
    writer.writerow(["carlos.lopez@empresa.com", "Carlos Lopez", "Ventas",           "employee"])
    writer.writerow(["marta.ruiz@empresa.com",   "Marta Ruiz",   "Tecnologia",       "manager"])
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=plantilla_empleados.csv"},
    )


@router.post("/csv/preview")
async def preview_csv_import(body: dict, current_user: dict = Depends(get_current_user)):
    from app.services.bulk_import import preview_csv
    return await preview_csv(body.get("csv_content", ""), body.get("entity_type", "employees"))


@limiter.limit("5/minute")
@router.post("/csv/import")
async def csv_import_bulk(
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "super_admin", "admin"]))
):
    from app.services.bulk_import import import_csv
    user_id = current_user.get("sub", "").split("|")[-1]
    return await import_csv(db, body.get("csv_content", ""), body.get("entity_type", "employees"), user_id, body.get("dry_run", False))
