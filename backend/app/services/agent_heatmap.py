import logging
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract
from datetime import datetime, timezone, timedelta
from collections import defaultdict

logger = logging.getLogger("successcore.heatmap")


async def get_agent_heatmap(db: AsyncSession, days: int = 30) -> dict:
    from app.models.agent import AgentExecutionRun

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(AgentExecutionRun).where(AgentExecutionRun.created_at >= cutoff)
    )
    runs = result.scalars().all()

    by_hour: Dict[int, int] = defaultdict(int)
    by_day: Dict[str, int] = defaultdict(int)
    by_hour_day: Dict[str, int] = defaultdict(int)

    for r in runs:
        if r.created_at:
            hour = r.created_at.hour
            day = r.created_at.strftime("%a")
            by_hour[hour] += 1
            by_day[day] += 1
            by_hour_day[f"{day}-{hour:02d}"] += 1

    total = len(runs)
    if total == 0:
        return {"total_runs": 0, "days_analyzed": days}

    peak_hour = max(by_hour, key=by_hour.get)
    peak_day = max(by_day, key=by_day.get)
    peak_hour_day = max(by_hour_day, key=by_hour_day.get)

    hours = [{"hour": h, "count": by_hour.get(h, 0), "pct": round(by_hour.get(h, 0) / max(total, 1) * 100, 1)} for h in range(24)]
    days = [{"day": d, "count": by_day.get(d, 0), "pct": round(by_day.get(d, 0) / max(total, 1) * 100, 1)} for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]

    top_slots = sorted(by_hour_day.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total_runs": total,
        "days_analyzed": days,
        "peak_hour": peak_hour,
        "peak_day": peak_day,
        "peak_time_slot": peak_hour_day,
        "hourly_distribution": hours,
        "daily_distribution": days,
        "busiest_slots": [{"slot": s, "count": c} for s, c in top_slots],
    }
