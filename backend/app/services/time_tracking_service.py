import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

logger = logging.getLogger("successcore.time_tracking")


async def clock_in(
    db: AsyncSession,
    user_id: str,
    notes: str = "",
    project_id: str = "",
    task_id: str = "",
) -> Dict[str, Any]:
    from app.models.finance import TimeLog

    active = await db.execute(
        select(TimeLog).where(
            and_(TimeLog.user_id == user_id, TimeLog.clock_out == None)
        )
    )
    if active.scalar_one_or_none():
        raise ValueError("User already has an active clock-in session")

    entry = TimeLog(
        id=uuid.uuid4().hex,
        user_id=user_id,
        clock_in=datetime.now(timezone.utc),
        notes=notes,
        project_id=project_id or None,
        task_id=task_id or None,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return {"id": entry.id, "clock_in": entry.clock_in.isoformat(), "status": "active"}


async def clock_out(
    db: AsyncSession,
    user_id: str,
    notes: str = "",
) -> Dict[str, Any]:
    from app.models.finance import TimeLog

    active = await db.execute(
        select(TimeLog).where(
            and_(TimeLog.user_id == user_id, TimeLog.clock_out == None)
        ).order_by(TimeLog.clock_in.desc()).limit(1)
    )
    entry = active.scalar_one_or_none()
    if not entry:
        raise ValueError("No active clock-in session found")

    entry.clock_out = datetime.now(timezone.utc)
    entry.notes = (entry.notes or "") + (" | " + notes if notes else "")
    await db.commit()
    await db.refresh(entry)

    duration = (entry.clock_out - entry.clock_in).total_seconds() / 3600
    return {
        "id": entry.id,
        "clock_in": entry.clock_in.isoformat(),
        "clock_out": entry.clock_out.isoformat(),
        "duration_hours": round(duration, 2),
        "status": "completed",
    }


async def get_time_logs(
    db: AsyncSession,
    user_id: str = "",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    from app.models.finance import TimeLog

    query = select(TimeLog).order_by(TimeLog.clock_in.desc())
    if user_id:
        query = query.where(TimeLog.user_id == user_id)
    if start_date:
        query = query.where(TimeLog.clock_in >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.where(TimeLog.clock_in <= datetime.fromisoformat(end_date))

    result = await db.execute(query.limit(limit))
    entries = result.scalars().all()

    return [
        {
            "id": e.id, "user_id": e.user_id,
            "clock_in": e.clock_in.isoformat() if e.clock_in else None,
            "clock_out": e.clock_out.isoformat() if e.clock_out else None,
            "notes": e.notes, "project_id": getattr(e, "project_id", ""),
            "task_id": getattr(e, "task_id", ""),
        }
        for e in entries
    ]


async def get_active_session(db: AsyncSession, user_id: str) -> Optional[Dict[str, Any]]:
    from app.models.finance import TimeLog

    result = await db.execute(
        select(TimeLog).where(
            and_(TimeLog.user_id == user_id, TimeLog.clock_out == None)
        ).order_by(TimeLog.clock_in.desc()).limit(1)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        return None

    now = datetime.now(timezone.utc)
    elapsed = (now - entry.clock_in).total_seconds() / 3600
    return {
        "id": entry.id,
        "clock_in": entry.clock_in.isoformat(),
        "elapsed_hours": round(elapsed, 2),
        "notes": entry.notes,
        "project_id": getattr(entry, "project_id", ""),
        "task_id": getattr(entry, "task_id", ""),
        "active": True,
    }


async def get_timesheet_summary(
    db: AsyncSession,
    user_id: str = "",
    start_date: str = "",
    end_date: str = "",
) -> Dict[str, Any]:
    from app.models.finance import TimeLog

    start = datetime.fromisoformat(start_date) if start_date else datetime.now(timezone.utc) - timedelta(days=30)
    end = datetime.fromisoformat(end_date) if end_date else datetime.now(timezone.utc)

    query = select(TimeLog).where(
        and_(TimeLog.clock_in >= start, TimeLog.clock_in <= end)
    )
    if user_id:
        query = query.where(TimeLog.user_id == user_id)

    result = await db.execute(query.order_by(TimeLog.clock_in.asc()))
    entries = result.scalars().all()

    total_hours = 0.0
    daily_hours: Dict[str, float] = {}
    project_hours: Dict[str, float] = {}

    for e in entries:
        if e.clock_out:
            hours = (e.clock_out - e.clock_in).total_seconds() / 3600
        else:
            hours = 0
        total_hours += hours

        day = e.clock_in.date().isoformat()
        daily_hours[day] = daily_hours.get(day, 0) + hours

        project = getattr(e, "project_id", "") or "No project"
        project_hours[project] = project_hours.get(project, 0) + hours

    return {
        "period": f"{start.date().isoformat()} to {end.date().isoformat()}",
        "total_hours": round(total_hours, 2),
        "total_entries": len(entries),
        "daily_breakdown": {d: round(h, 2) for d, h in sorted(daily_hours.items())},
        "project_breakdown": {p: round(h, 2) for p, h in sorted(project_hours.items(), key=lambda x: -x[1])[:10]},
    }
