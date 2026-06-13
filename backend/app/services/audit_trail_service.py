import logging
import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.employee_history import EmployeeHistory

logger = logging.getLogger("successcore.audit_trail")


async def log_employee_change(
    db: AsyncSession,
    employee_id: str,
    field_name: str,
    old_value: Any,
    new_value: Any,
    changed_by: str = "",
    changed_by_name: str = "",
    reason: str = "",
    source: str = "manual",
):
    if str(old_value) == str(new_value) and old_value is not None and new_value is not None:
        return

    entry = EmployeeHistory(
        id=uuid.uuid4().hex,
        employee_id=employee_id,
        field_name=field_name,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        changed_by=changed_by,
        changed_by_name=changed_by_name,
        change_reason=reason,
        source=source,
    )
    db.add(entry)
    logger.info(f"Audit trail: employee={employee_id[:8]} field={field_name} by={changed_by_name or changed_by[:8]}")


async def get_employee_history(
    db: AsyncSession,
    employee_id: str,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(EmployeeHistory)
        .where(EmployeeHistory.employee_id == employee_id)
        .order_by(desc(EmployeeHistory.created_at))
        .limit(limit)
    )
    entries = result.scalars().all()

    return [
        {
            "id": e.id,
            "field_name": e.field_name,
            "old_value": e.old_value,
            "new_value": e.new_value,
            "changed_by": e.changed_by,
            "changed_by_name": e.changed_by_name,
            "change_reason": e.change_reason,
            "source": e.source,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


async def get_field_history(
    db: AsyncSession,
    employee_id: str,
    field_name: str,
) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(EmployeeHistory)
        .where(EmployeeHistory.employee_id == employee_id, EmployeeHistory.field_name == field_name)
        .order_by(desc(EmployeeHistory.created_at))
        .limit(20)
    )
    entries = result.scalars().all()
    return [
        {"id": e.id, "old_value": e.old_value, "new_value": e.new_value,
         "changed_by_name": e.changed_by_name, "created_at": e.created_at.isoformat() if e.created_at else None}
        for e in entries
    ]


async def get_audit_summary(
    db: AsyncSession,
    days: int = 7,
) -> Dict[str, Any]:
    from sqlalchemy import func
    from datetime import datetime, timezone, timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    total_res = await db.execute(
        select(func.count(EmployeeHistory.id)).where(EmployeeHistory.created_at >= cutoff)
    )
    total = total_res.scalar() or 0

    unique_employees = await db.execute(
        select(func.count(func.distinct(EmployeeHistory.employee_id)))
        .where(EmployeeHistory.created_at >= cutoff)
    )
    unique_emp = unique_employees.scalar() or 0

    field_res = await db.execute(
        select(EmployeeHistory.field_name, func.count(EmployeeHistory.id).label("cnt"))
        .where(EmployeeHistory.created_at >= cutoff)
        .group_by(EmployeeHistory.field_name)
        .order_by(desc("cnt"))
        .limit(10)
    )
    by_field = {row.field_name: row.cnt for row in field_res.all()}

    source_res = await db.execute(
        select(EmployeeHistory.source, func.count(EmployeeHistory.id).label("cnt"))
        .where(EmployeeHistory.created_at >= cutoff)
        .group_by(EmployeeHistory.source)
    )
    by_source = {row.source: row.cnt for row in source_res.all()}

    return {
        "period_days": days,
        "total_changes": total,
        "unique_employees_changed": unique_emp,
        "changes_by_field": by_field,
        "changes_by_source": by_source,
    }
