import logging
from typing import List, Dict, Optional

logger = logging.getLogger("successcore.import_preview")

DEFAULT_COLUMNS = ["email", "full_name", "department", "role", "base_salary", "country", "contract_type"]


def preview_csv_row(row: dict, row_index: int, existing_emails: set) -> dict:
    errors = []
    warnings = []
    email = str(row.get("email", "") or "").strip()

    if not email:
        errors.append("Email is required")
    elif "@" not in email:
        errors.append(f"Invalid email: {email}")

    if email in existing_emails:
        warnings.append(f"Email already exists in system: {email}")

    full_name = str(row.get("full_name", "") or "").strip()
    if len(full_name) > 200:
        errors.append("Name exceeds 200 characters")
    if not full_name:
        warnings.append("Full name is empty")

    department = str(row.get("department", "") or "").strip()
    role = str(row.get("role", "employee") or "employee").strip()

    valid_roles = {"hr_admin", "employee", "manager", "viewer"}
    if role not in valid_roles:
        errors.append(f"Invalid role '{role}'. Valid: {valid_roles}")

    salary_raw = row.get("base_salary", 0)
    try:
        salary = float(salary_raw) if salary_raw else 0.0
    except (ValueError, TypeError):
        errors.append(f"Invalid salary: {salary_raw}")
        salary = 0.0

    return {
        "row": row_index + 1,
        "email": email,
        "full_name": full_name,
        "department": department,
        "role": role,
        "salary": salary,
        "errors": errors,
        "warnings": warnings,
        "status": "error" if errors else "warning" if warnings else "ok",
    }


async def preview_import(file_path: str, db) -> dict:
    import pandas as pd
    from app.models.user import User
    from sqlalchemy import select

    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    existing_res = await db.execute(select(User.email))
    existing_emails = set(existing_res.scalars().all())

    rows = df.to_dict("records")
    preview = [preview_csv_row(r, i, existing_emails) for i, r in enumerate(rows)]

    ok_count = sum(1 for p in preview if p["status"] == "ok")
    warn_count = sum(1 for p in preview if p["status"] == "warning")
    error_count = sum(1 for p in preview if p["status"] == "error")

    return {
        "total_rows": len(rows),
        "will_insert": ok_count,
        "will_insert_with_warnings": warn_count,
        "will_reject": error_count,
        "errors_summary": [p for p in preview if p["status"] == "error"][:50],
        "preview": preview[:100],
    }
