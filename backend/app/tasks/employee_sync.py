"""
employee_sync.py — Tarea Celery de carga masiva robusta.

Mejoras de seguridad y robustez:
  - Transacciones atómicas con SAVEPOINT por chunk (rollback granular).
  - UPSERT con ON CONFLICT (email) DO NOTHING — sin SELECT previo costoso.
  - Validación por fila (email regex, longitud de campos) antes del DB write.
  - Reporte de row_errors detallado (fila, motivo de rechazo).
  - Limpieza automática del archivo temporal tras el procesamiento.
  - Timeout configurable vía Celery (600s hard / 540s soft).
  - Logging estructurado con contadores insertados / duplicados / rechazados.
"""

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.logger import logger
import pandas as pd
import time
import uuid
import re
import os
from datetime import datetime, date, timezone

# ─── Engine sincrónico al schema de metadata (opcional si necesitas metadatos)
# Pero nos interesa conectarnos al schema del tenant dinámicamente
sync_global_uri = settings.SYNC_DATABASE_URI
sync_engine = create_engine(sync_global_uri, pool_pre_ping=True)

# ─── Constantes de validación ─────────────────────────────────────────────────
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
CHUNK_SIZE   = 2000   # filas por chunk (más pequeño = SAVEPOINT más seguro)
ALLOWED_ROLES = {"hr_admin", "employee", "manager", "viewer"}

# ─── Validación por fila ──────────────────────────────────────────────────────
def _validate_row(row: dict) -> str | None:
    """
    Valida una fila del CSV/Excel.
    Retorna None si es válida, o un string con el motivo de rechazo.
    """
    email = str(row.get("email", "") or "").strip()
    if not email:
        return "Email vacío"
    if not EMAIL_REGEX.match(email):
        return f"Email inválido: '{email}'"

    full_name = str(row.get("full_name", "") or "")
    if len(full_name) > 200:
        return f"full_name supera 200 caracteres"

    department = str(row.get("department", "") or "")
    if len(department) > 100:
        return "department supera 100 caracteres"

    role = str(row.get("role", "employee") or "employee").strip()
    if role and role not in ALLOWED_ROLES:
        return f"Role desconocido: '{role}'. Valores: {ALLOWED_ROLES}"

    return None


# ─── Proceso Principal ────────────────────────────────────────────────────────
def process_employees_file(file_path: str, tenant_id: str, progress_callback=None):
    """
    Procesar CSV/Excel de miles de empleados de forma síncrona/background.

    Flujo por chunk:
      1. Validar cada fila → separar válidas / row_errors.
      2. Dentro de un SAVEPOINT, insertar con ON CONFLICT (email) DO NOTHING.
      3. Confirmar SAVEPOINT si OK, hacer ROLLBACK TO SAVEPOINT si falla.
      4. Actualizar progreso.
    """
    logger.info(f"[sync] Iniciando carga masiva para tenant={tenant_id}, file={file_path}")

    # Determinar si es SQLite para evitar prefijos de esquema
    is_sqlite = "sqlite" in str(sync_engine.url)
    table_name = "users" if is_sqlite else f"tenant_{tenant_id}.users"

    # ── 1. Cargar archivo ────────────────────────────────────────────────────
    try:
        if file_path.endswith(".xlsx"):
            df_full = pd.read_excel(file_path, engine="openpyxl")
            total_rows = len(df_full)
            chunks = [df_full.iloc[i:i + CHUNK_SIZE].copy() for i in range(0, total_rows, CHUNK_SIZE)]
        else:
            with open(file_path, "r", encoding="utf-8-sig") as fh:
                total_rows = sum(1 for _ in fh) - 1
            chunks = pd.read_csv(file_path, chunksize=CHUNK_SIZE, skipinitialspace=True, encoding="utf-8-sig")
    except Exception as exc:
        err = f"Error cargando archivo: {exc}"
        logger.error(f"[sync] {err}")
        if progress_callback:
            progress_callback("FAILURE", {"error": err})
        _cleanup(file_path)
        return {"status": "failed", "error": err}

    # ── 2. Procesar por chunks ────────────────────────────────────────────────
    inserted   = 0
    duplicates = 0
    rejected   = 0
    row_errors: list[dict] = []
    chunk_index = 0

    with sync_engine.connect() as conn:
        for raw_chunk in chunks:
            chunk_index += 1
            raw_chunk.columns = raw_chunk.columns.str.lower().str.strip().str.replace(" ", "_")

            if "password" in raw_chunk.columns:
                raw_chunk.drop(columns=["password"], inplace=True)

            raw_chunk["role"] = raw_chunk.get("role", pd.Series("employee", index=raw_chunk.index)).fillna("employee")
            now = datetime.now(timezone.utc)

            valid_rows: list[dict] = []
            for local_idx, row in enumerate(raw_chunk.to_dict(orient="records")):
                error_msg = _validate_row(row)
                if error_msg:
                    rejected += 1
                    if len(row_errors) < 500:
                        row_errors.append({
                            "chunk": chunk_index,
                            "local_row": local_idx + 1,
                            "email": str(row.get("email", ""))[:120],
                            "reason": error_msg,
                        })
                else:
                    valid_rows.append(row)

            if not valid_rows:
                continue

            savepoint_name = f"sp_chunk_{chunk_index}"
            try:
                conn.execute(text(f"SAVEPOINT {savepoint_name}"))

                chunk_inserted = 0
                chunk_duplicates = 0

                for row in valid_rows:
                    email     = str(row.get("email", "")).strip().lower()
                    full_name = str(row.get("full_name", "") or "")[:200] or None
                    department= str(row.get("department", "") or "")[:100] or None
                    role      = str(row.get("role", "employee") or "employee")[:50]

                    # Ajustar ON CONFLICT para SQLite vs Postgres
                    conflict_clause = "ON CONFLICT (email) DO NOTHING"

                    result = conn.execute(
                        text(f"""
                            INSERT INTO {table_name}
                                (id, email, full_name, department, role, is_active, created_at, updated_at)
                            VALUES
                                (:id, :email, :full_name, :department, :role, true, :now, :now)
                            {conflict_clause}
                        """),
                        {
                            "id":         uuid.uuid4().hex,
                            "email":      email,
                            "full_name":  full_name,
                            "department": department,
                            "role":       role,
                            "now":        now,
                        }
                    )
                    # En SQLAlchemy 2.0 con SQLite DO NOTHING devuelve rowcount=0 cuando ignora
                    if result.rowcount == 1:
                        chunk_inserted += 1
                    else:
                        chunk_duplicates += 1

                conn.execute(text(f"RELEASE SAVEPOINT {savepoint_name}"))
                conn.commit()

                inserted   += chunk_inserted
                duplicates += chunk_duplicates

                logger.info(
                    f"[sync] chunk={chunk_index} | +{chunk_inserted} insertados | {chunk_duplicates} duplicados | {rejected} rechazados"
                )

            except Exception as exc:
                try:
                    conn.execute(text(f"ROLLBACK TO SAVEPOINT {savepoint_name}"))
                    conn.commit()
                except Exception:
                    pass

                err_msg = str(exc)
                logger.error(f"[sync] Error en chunk {chunk_index}: {err_msg}")
                if len(row_errors) < 500:
                    row_errors.append({
                        "chunk": chunk_index,
                        "local_row": 0,
                        "email": "N/A",
                        "reason": f"Error DB en chunk completo: {err_msg[:200]}",
                    })

            processed_approx = (chunk_index * CHUNK_SIZE)
            if progress_callback:
                progress_callback("PROCESSING", {
                    "inserted":   inserted,
                    "duplicates": duplicates,
                    "rejected":   rejected,
                    "total":      total_rows,
                    "progress_percent": min(int((processed_approx / max(total_rows, 1)) * 100), 99),
                })

    # ── 3. Limpieza del archivo temporal ────────────────────────────────────
    _cleanup(file_path)

    summary = {
        "status":     "completed",
        "inserted":   inserted,
        "duplicates": duplicates,
        "rejected":   rejected,
        "row_errors": row_errors[:50],  # devolver máx 50 en el resultado final
        "total_processed": inserted + duplicates,
    }
    logger.info(f"[sync] Finalizado. {summary}")
    return summary


def _cleanup(file_path: str):
    """Elimina el archivo temporal de upload tras el procesamiento."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"[sync] Archivo temporal eliminado: {file_path}")
    except Exception as exc:
        logger.warning(f"[sync] No se pudo eliminar el archivo temporal: {exc}")


# ─── Candidate Processor ─────────────────────────────────────────────────────
def process_candidates_file(file_path: str, tenant_id: str, progress_callback=None):
    logger.info(f"[sync] Iniciando carga masiva de candidatos para tenant={tenant_id}, file={file_path}")

    is_sqlite = "sqlite" in str(sync_engine.url)
    jobs_table = "hire_jobs" if is_sqlite else f"tenant_{tenant_id}.hire_jobs"
    table_name = "hire_candidates" if is_sqlite else f"tenant_{tenant_id}.hire_candidates"

    try:
        if file_path.endswith(".xlsx"):
            df_full = pd.read_excel(file_path, engine="openpyxl")
            total_rows = len(df_full)
            chunks = [df_full.iloc[i:i + CHUNK_SIZE].copy() for i in range(0, total_rows, CHUNK_SIZE)]
        else:
            with open(file_path, "r", encoding="utf-8-sig") as fh:
                total_rows = sum(1 for _ in fh) - 1
            chunks = pd.read_csv(file_path, chunksize=CHUNK_SIZE, skipinitialspace=True, encoding="utf-8-sig")
    except Exception as exc:
        err = f"Error cargando archivo: {exc}"
        logger.error(f"[sync] {err}")
        if progress_callback:
            progress_callback("FAILURE", {"error": err})
        _cleanup(file_path)
        return {"status": "failed", "error": err}

    inserted = 0
    duplicates = 0
    rejected = 0
    row_errors: list[dict] = []
    chunk_index = 0
    now = datetime.now(timezone.utc)

    with sync_engine.connect() as conn:
        # Cache known job IDs for validation
        known_job_ids = set()
        try:
            job_rows = conn.execute(text(f"SELECT id FROM {jobs_table}")).fetchall()
            known_job_ids = {r[0] for r in job_rows}
        except Exception:
            pass

        for raw_chunk in chunks:
            chunk_index += 1
            raw_chunk.columns = raw_chunk.columns.str.lower().str.strip().str.replace(" ", "_")

            if "password" in raw_chunk.columns:
                raw_chunk.drop(columns=["password"], inplace=True)

            valid_rows: list[dict] = []
            for local_idx, row in enumerate(raw_chunk.to_dict(orient="records")):
                email = str(row.get("email", "") or "").strip()
                first_name = str(row.get("first_name", "") or "").strip()
                last_name = str(row.get("last_name", "") or "").strip()
                job_id = str(row.get("job_id", "") or "").strip()

                error_msg = None
                if not email:
                    error_msg = "Email vacio"
                elif not EMAIL_REGEX.match(email):
                    error_msg = f"Email invalido: '{email}'"
                elif not first_name:
                    error_msg = "first_name vacio"
                elif not last_name:
                    error_msg = "last_name vacio"
                elif not job_id:
                    error_msg = "job_id vacio"
                elif known_job_ids and job_id not in known_job_ids:
                    error_msg = f"job_id no existe: '{job_id}'"

                if error_msg:
                    rejected += 1
                    if len(row_errors) < 500:
                        row_errors.append({
                            "chunk": chunk_index,
                            "local_row": local_idx + 1,
                            "email": email[:120],
                            "reason": error_msg,
                        })
                else:
                    valid_rows.append(row)

            if not valid_rows:
                continue

            savepoint_name = f"sp_chunk_{chunk_index}"
            try:
                conn.execute(text(f"SAVEPOINT {savepoint_name}"))
                chunk_inserted = 0

                for row in valid_rows:
                    email = str(row.get("email", "")).strip().lower()
                    first_name = str(row.get("first_name", "") or "")[:100]
                    last_name = str(row.get("last_name", "") or "")[:100]
                    job_id = str(row.get("job_id", "") or "").strip()
                    phone = str(row.get("phone", "") or "")[:50] or None
                    stage = str(row.get("stage", "applied") or "applied")[:50]
                    source = str(row.get("source", "") or "")[:100] or None
                    linkedin_url = str(row.get("linkedin_url", "") or "")[:255] or None

                    conflict_clause = "ON CONFLICT (email) DO NOTHING"

                    result = conn.execute(
                        text(f"""
                            INSERT INTO {table_name}
                                (id, job_id, first_name, last_name, email, phone, stage, source, linkedin_url, created_at, updated_at)
                            VALUES
                                (:id, :job_id, :first_name, :last_name, :email, :phone, :stage, :source, :linkedin_url, :now, :now)
                            {conflict_clause}
                        """),
                        {
                            "id": uuid.uuid4().hex,
                            "job_id": job_id,
                            "first_name": first_name,
                            "last_name": last_name,
                            "email": email,
                            "phone": phone,
                            "stage": stage,
                            "source": source,
                            "linkedin_url": linkedin_url,
                            "now": now,
                        }
                    )
                    if result.rowcount == 1:
                        chunk_inserted += 1

                conn.execute(text(f"RELEASE SAVEPOINT {savepoint_name}"))
                conn.commit()
                inserted += chunk_inserted

                logger.info(f"[sync] chunk={chunk_index} | +{chunk_inserted} candidates insertados | {rejected} rechazados")

            except Exception as exc:
                try:
                    conn.execute(text(f"ROLLBACK TO SAVEPOINT {savepoint_name}"))
                    conn.commit()
                except Exception:
                    pass
                logger.error(f"[sync] Error en chunk {chunk_index}: {exc}")
                if len(row_errors) < 500:
                    row_errors.append({
                        "chunk": chunk_index,
                        "local_row": 0,
                        "email": "N/A",
                        "reason": f"Error DB en chunk completo: {str(exc)[:200]}",
                    })

            processed_approx = (chunk_index * CHUNK_SIZE)
            if progress_callback:
                progress_callback("PROCESSING", {
                    "inserted": inserted,
                    "duplicates": duplicates,
                    "rejected": rejected,
                    "total": total_rows,
                    "progress_percent": min(int((processed_approx / max(total_rows, 1)) * 100), 99),
                })

    _cleanup(file_path)
    summary = {
        "status": "completed",
        "inserted": inserted,
        "duplicates": duplicates,
        "rejected": rejected,
        "row_errors": row_errors[:50],
        "total_processed": inserted + duplicates,
    }
    logger.info(f"[sync] Candidatos finalizado. {summary}")
    return summary


# ─── Course Processor ─────────────────────────────────────────────────────────
def process_courses_file(file_path: str, tenant_id: str, progress_callback=None):
    logger.info(f"[sync] Iniciando carga masiva de cursos para tenant={tenant_id}, file={file_path}")

    is_sqlite = "sqlite" in str(sync_engine.url)
    table_name = "courses" if is_sqlite else f"tenant_{tenant_id}.courses"

    try:
        if file_path.endswith(".xlsx"):
            df_full = pd.read_excel(file_path, engine="openpyxl")
            total_rows = len(df_full)
            chunks = [df_full.iloc[i:i + CHUNK_SIZE].copy() for i in range(0, total_rows, CHUNK_SIZE)]
        else:
            with open(file_path, "r", encoding="utf-8-sig") as fh:
                total_rows = sum(1 for _ in fh) - 1
            chunks = pd.read_csv(file_path, chunksize=CHUNK_SIZE, skipinitialspace=True, encoding="utf-8-sig")
    except Exception as exc:
        err = f"Error cargando archivo: {exc}"
        logger.error(f"[sync] {err}")
        if progress_callback:
            progress_callback("FAILURE", {"error": err})
        _cleanup(file_path)
        return {"status": "failed", "error": err}

    inserted = 0
    duplicates = 0
    rejected = 0
    row_errors: list[dict] = []
    chunk_index = 0
    now = datetime.now(timezone.utc)

    with sync_engine.connect() as conn:
        for raw_chunk in chunks:
            chunk_index += 1
            raw_chunk.columns = raw_chunk.columns.str.lower().str.strip().str.replace(" ", "_")

            valid_rows: list[dict] = []
            for local_idx, row in enumerate(raw_chunk.to_dict(orient="records")):
                title = str(row.get("title", "") or "").strip()
                error_msg = None
                if not title:
                    error_msg = "title vacio"
                if error_msg:
                    rejected += 1
                    if len(row_errors) < 500:
                        row_errors.append({
                            "chunk": chunk_index,
                            "local_row": local_idx + 1,
                            "title": title[:120],
                            "reason": error_msg,
                        })
                else:
                    valid_rows.append(row)

            if not valid_rows:
                continue

            savepoint_name = f"sp_chunk_{chunk_index}"
            try:
                conn.execute(text(f"SAVEPOINT {savepoint_name}"))
                chunk_inserted = 0

                for row in valid_rows:
                    title = str(row.get("title", "") or "")[:200]
                    description = str(row.get("description", "") or "") or None
                    is_scorm = str(row.get("is_scorm", "false")).strip().lower() in ("true", "1", "yes", "si")
                    scorm_version = str(row.get("scorm_version", "") or "")[:20] or None
                    package_url = str(row.get("package_url", "") or "")[:500] or None
                    min_duration = _safe_float(row.get("min_duration_hours"), 2.0)
                    is_fundae = str(row.get("is_fundae_eligible", "true")).strip().lower() in ("true", "1", "yes", "si")

                    result = conn.execute(
                        text(f"""
                            INSERT INTO {table_name}
                                (id, title, description, is_scorm, scorm_version, package_url,
                                 min_duration_hours, is_fundae_eligible, created_at)
                            VALUES
                                (:id, :title, :description, :is_scorm, :scorm_version, :package_url,
                                 :min_duration_hours, :is_fundae_eligible, :now)
                        """),
                        {
                            "id": uuid.uuid4().hex,
                            "title": title,
                            "description": description,
                            "is_scorm": is_scorm,
                            "scorm_version": scorm_version,
                            "package_url": package_url,
                            "min_duration_hours": min_duration,
                            "is_fundae_eligible": is_fundae,
                            "now": now,
                        }
                    )
                    if result.rowcount == 1:
                        chunk_inserted += 1

                conn.execute(text(f"RELEASE SAVEPOINT {savepoint_name}"))
                conn.commit()
                inserted += chunk_inserted

                logger.info(f"[sync] chunk={chunk_index} | +{chunk_inserted} courses insertados | {rejected} rechazados")

            except Exception as exc:
                try:
                    conn.execute(text(f"ROLLBACK TO SAVEPOINT {savepoint_name}"))
                    conn.commit()
                except Exception:
                    pass
                logger.error(f"[sync] Error en chunk {chunk_index}: {exc}")
                if len(row_errors) < 500:
                    row_errors.append({
                        "chunk": chunk_index,
                        "local_row": 0,
                        "title": "N/A",
                        "reason": f"Error DB en chunk completo: {str(exc)[:200]}",
                    })

            processed_approx = (chunk_index * CHUNK_SIZE)
            if progress_callback:
                progress_callback("PROCESSING", {
                    "inserted": inserted,
                    "duplicates": duplicates,
                    "rejected": rejected,
                    "total": total_rows,
                    "progress_percent": min(int((processed_approx / max(total_rows, 1)) * 100), 99),
                })

    _cleanup(file_path)
    summary = {
        "status": "completed",
        "inserted": inserted,
        "duplicates": duplicates,
        "rejected": rejected,
        "row_errors": row_errors[:50],
        "total_processed": inserted + duplicates,
    }
    logger.info(f"[sync] Cursos finalizado. {summary}")
    return summary


# ─── Expense Processor ────────────────────────────────────────────────────────
def process_expenses_file(file_path: str, tenant_id: str, progress_callback=None):
    logger.info(f"[sync] Iniciando carga masiva de gastos para tenant={tenant_id}, file={file_path}")

    is_sqlite = "sqlite" in str(sync_engine.url)
    table_name = "expense_claims" if is_sqlite else f"tenant_{tenant_id}.expense_claims"

    try:
        if file_path.endswith(".xlsx"):
            df_full = pd.read_excel(file_path, engine="openpyxl")
            total_rows = len(df_full)
            chunks = [df_full.iloc[i:i + CHUNK_SIZE].copy() for i in range(0, total_rows, CHUNK_SIZE)]
        else:
            with open(file_path, "r", encoding="utf-8-sig") as fh:
                total_rows = sum(1 for _ in fh) - 1
            chunks = pd.read_csv(file_path, chunksize=CHUNK_SIZE, skipinitialspace=True, encoding="utf-8-sig")
    except Exception as exc:
        err = f"Error cargando archivo: {exc}"
        logger.error(f"[sync] {err}")
        if progress_callback:
            progress_callback("FAILURE", {"error": err})
        _cleanup(file_path)
        return {"status": "failed", "error": err}

    inserted = 0
    duplicates = 0
    rejected = 0
    row_errors: list[dict] = []
    chunk_index = 0
    now = datetime.now(timezone.utc)

    with sync_engine.connect() as conn:
        for raw_chunk in chunks:
            chunk_index += 1
            raw_chunk.columns = raw_chunk.columns.str.lower().str.strip().str.replace(" ", "_")

            valid_rows: list[dict] = []
            for local_idx, row in enumerate(raw_chunk.to_dict(orient="records")):
                merchant = str(row.get("merchant", "") or "").strip()
                date_str = str(row.get("date", "") or "").strip()
                amount_str = str(row.get("total_amount", "") or "").strip()
                error_msg = None
                if not merchant:
                    error_msg = "merchant vacio"
                elif not date_str:
                    error_msg = "date vacio"
                elif not amount_str:
                    error_msg = "total_amount vacio"
                elif not _is_valid_date(date_str):
                    error_msg = f"date invalido: '{date_str}'"
                elif not _is_valid_amount(amount_str):
                    error_msg = f"total_amount invalido: '{amount_str}'"

                if error_msg:
                    rejected += 1
                    if len(row_errors) < 500:
                        row_errors.append({
                            "chunk": chunk_index,
                            "local_row": local_idx + 1,
                            "merchant": merchant[:120],
                            "reason": error_msg,
                        })
                else:
                    valid_rows.append(row)

            if not valid_rows:
                continue

            savepoint_name = f"sp_chunk_{chunk_index}"
            try:
                conn.execute(text(f"SAVEPOINT {savepoint_name}"))
                chunk_inserted = 0

                for row in valid_rows:
                    merchant = str(row.get("merchant", "") or "")[:150]
                    date_val = _parse_date(str(row.get("date", "") or "").strip())
                    total_amount = _safe_float(row.get("total_amount"), 0.0)
                    tax_amount = _safe_float(row.get("tax_amount"), 0.0)
                    status = str(row.get("status", "pending") or "pending")[:30]
                    category = str(row.get("category", "other") or "other")[:50]
                    description = str(row.get("description", "") or "") or None

                    result = conn.execute(
                        text(f"""
                            INSERT INTO {table_name}
                                (id, user_id, merchant, date, total_amount, tax_amount, status, category, comments, created_at)
                            VALUES
                                (:id, :user_id, :merchant, :date, :total_amount, :tax_amount, :status, :category, :comments, :now)
                        """),
                        {
                            "id": uuid.uuid4().hex,
                            "user_id": "00000000000000000000000000000000",
                            "merchant": merchant,
                            "date": date_val,
                            "total_amount": total_amount,
                            "tax_amount": tax_amount,
                            "status": status,
                            "category": category,
                            "comments": description,
                            "now": now,
                        }
                    )
                    if result.rowcount == 1:
                        chunk_inserted += 1

                conn.execute(text(f"RELEASE SAVEPOINT {savepoint_name}"))
                conn.commit()
                inserted += chunk_inserted

                logger.info(f"[sync] chunk={chunk_index} | +{chunk_inserted} expenses insertados | {rejected} rechazados")

            except Exception as exc:
                try:
                    conn.execute(text(f"ROLLBACK TO SAVEPOINT {savepoint_name}"))
                    conn.commit()
                except Exception:
                    pass
                logger.error(f"[sync] Error en chunk {chunk_index}: {exc}")
                if len(row_errors) < 500:
                    row_errors.append({
                        "chunk": chunk_index,
                        "local_row": 0,
                        "merchant": "N/A",
                        "reason": f"Error DB en chunk completo: {str(exc)[:200]}",
                    })

            processed_approx = (chunk_index * CHUNK_SIZE)
            if progress_callback:
                progress_callback("PROCESSING", {
                    "inserted": inserted,
                    "duplicates": duplicates,
                    "rejected": rejected,
                    "total": total_rows,
                    "progress_percent": min(int((processed_approx / max(total_rows, 1)) * 100), 99),
                })

    _cleanup(file_path)
    summary = {
        "status": "completed",
        "inserted": inserted,
        "duplicates": duplicates,
        "rejected": rejected,
        "row_errors": row_errors[:50],
        "total_processed": inserted + duplicates,
    }
    logger.info(f"[sync] Gastos finalizado. {summary}")
    return summary


# ─── Helper Functions ─────────────────────────────────────────────────────────
def _safe_float(value, default=0.0):
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return default


def _is_valid_date(date_str: str) -> bool:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            datetime.strptime(date_str, fmt)
            return True
        except ValueError:
            continue
    return False


def _parse_date(date_str: str) -> date:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return date.today()


def _is_valid_amount(amount_str: str) -> bool:
    try:
        float(amount_str.replace(",", "."))
        return True
    except ValueError:
        return False
