import logging
import csv
import io
import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("successcore.bulk_import")

SUPPORTED_ENTITIES = ["employees", "candidates", "courses", "expenses"]


async def preview_csv(csv_content: str, entity_type: str) -> Dict[str, Any]:
    if entity_type not in SUPPORTED_ENTITIES:
        raise ValueError(f"Unsupported entity: {entity_type}. Supported: {', '.join(SUPPORTED_ENTITIES)}")

    reader = csv.DictReader(io.StringIO(csv_content))
    headers = reader.fieldnames or []
    rows = []
    errors = []
    line = 1

    for row in reader:
        line += 1
        cleaned = {k.strip().lower(): v.strip() if v else "" for k, v in row.items() if k}
        if not cleaned:
            continue
        row_errors = []

        if entity_type == "employees" and not cleaned.get("email"):
            row_errors.append("Missing required field: email")
        if entity_type == "employees" and not cleaned.get("full_name"):
            row_errors.append("Missing required field: full_name")
        if entity_type == "candidates" and not cleaned.get("email"):
            row_errors.append("Missing required field: email")

        rows.append(cleaned)
        if row_errors:
            errors.append({"line": line, "errors": row_errors})

    return {
        "entity_type": entity_type,
        "headers": headers,
        "total_rows": len(rows),
        "error_rows": len(errors),
        "errors": errors[:20],
        "sample": rows[:5],
        "ready": len(errors) == 0,
    }


async def import_csv(
    db: AsyncSession,
    csv_content: str,
    entity_type: str,
    user_id: str = "",
    dry_run: bool = True,
) -> Dict[str, Any]:
    preview = await preview_csv(csv_content, entity_type)
    if not preview["ready"]:
        return {"imported": 0, "errors": preview["errors"], "dry_run": dry_run}

    reader = csv.DictReader(io.StringIO(csv_content))
    rows = []
    for row in reader:
        cleaned = {k.strip().lower(): v.strip() if v else "" for k, v in row.items() if k}
        if cleaned:
            rows.append(cleaned)

    if dry_run:
        return {
            "imported": 0,
            "total": len(rows),
            "dry_run": True,
            "validation": "all rows valid",
            "sample": rows[:3],
        }

    imported = 0
    errors = []
    batch_id = uuid.uuid4().hex

    if entity_type == "employees":
        from app.models.user import User
        for i, row in enumerate(rows):
            try:
                employee = User(
                    id=uuid.uuid4().hex,
                    email=row.get("email", ""),
                    full_name=row.get("full_name", ""),
                    role=row.get("role", "employee"),
                    department=row.get("department", ""),
                    is_active=True,
                )
                if row.get("hire_date"):
                    from datetime import datetime
                    try:
                        employee.hire_date = datetime.fromisoformat(row["hire_date"])
                    except ValueError:
                        pass
                db.add(employee)
                imported += 1
            except Exception as e:
                errors.append({"row": i + 2, "error": str(e)[:200]})

    elif entity_type == "candidates":
        # Candidate usa first_name/last_name y "stage" (no full_name/status)
        from app.models.hire import Candidate
        for i, row in enumerate(rows):
            try:
                full_name = (row.get("full_name") or "").strip()
                first_name, _, last_name = full_name.partition(" ")
                candidate = Candidate(
                    id=uuid.uuid4().hex,
                    job_id=row.get("job_id", ""),
                    email=row.get("email", ""),
                    first_name=row.get("first_name") or first_name or "N/A",
                    last_name=row.get("last_name") or last_name or "N/A",
                    phone=row.get("phone", ""),
                    stage="applied",
                    notes=row.get("notes", ""),
                )
                db.add(candidate)
                imported += 1
            except Exception as e:
                errors.append({"row": i + 2, "error": str(e)[:200]})

    elif entity_type == "expenses":
        # Las notas de gastos se modelan con ExpenseClaim (app.models.finance)
        from datetime import date, datetime
        from app.models.finance import ExpenseClaim
        for i, row in enumerate(rows):
            try:
                expense_date = date.today()
                if row.get("date"):
                    try:
                        expense_date = datetime.fromisoformat(row["date"]).date()
                    except ValueError:
                        pass
                expense = ExpenseClaim(
                    id=uuid.uuid4().hex,
                    user_id=user_id,
                    merchant=row.get("merchant") or row.get("description") or "Desconocido",
                    date=expense_date,
                    total_amount=float(str(row.get("amount") or "0").replace(",", ".")),
                    category=row.get("category", "other"),
                    comments=row.get("description", ""),
                    status="pending",
                )
                db.add(expense)
                imported += 1
            except Exception as e:
                errors.append({"row": i + 2, "error": str(e)[:200]})

    elif entity_type == "courses":
        from app.models.training import Course
        for i, row in enumerate(rows):
            try:
                # Course no tiene columna "format"; is_scorm=False (por defecto) indica curso estándar
                course = Course(
                    id=uuid.uuid4().hex,
                    title=row.get("title", ""),
                    description=row.get("description", ""),
                )
                db.add(course)
                imported += 1
            except Exception as e:
                errors.append({"row": i + 2, "error": str(e)[:200]})

    await db.commit()
    logger.info(f"Bulk import ({entity_type}): {imported}/{len(rows)} rows, {len(errors)} errors, batch={batch_id[:8]}")
    return {
        "batch_id": batch_id,
        "entity_type": entity_type,
        "imported": imported,
        "total": len(rows),
        "errors": errors[:50],
        "dry_run": False,
    }
