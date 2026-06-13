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
        from app.models.hire import Candidate
        for i, row in enumerate(rows):
            try:
                candidate = Candidate(
                    id=uuid.uuid4().hex,
                    email=row.get("email", ""),
                    full_name=row.get("full_name", ""),
                    phone=row.get("phone", ""),
                    status="new",
                    notes=row.get("notes", ""),
                )
                db.add(candidate)
                imported += 1
            except Exception as e:
                errors.append({"row": i + 2, "error": str(e)[:200]})

    elif entity_type == "expenses":
        from app.models.finance import Expense
        for i, row in enumerate(rows):
            try:
                expense = Expense(
                    id=uuid.uuid4().hex,
                    description=row.get("description", ""),
                    amount_cents=int(float(row.get("amount", "0").replace(",", ".")) * 100),
                    category=row.get("category", "other"),
                    submitted_by=user_id,
                )
                db.add(expense)
                imported += 1
            except Exception as e:
                errors.append({"row": i + 2, "error": str(e)[:200]})

    elif entity_type == "courses":
        from app.models.training import Course
        for i, row in enumerate(rows):
            try:
                course = Course(
                    id=uuid.uuid4().hex,
                    title=row.get("title", ""),
                    description=row.get("description", ""),
                    format="self_paced",
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
