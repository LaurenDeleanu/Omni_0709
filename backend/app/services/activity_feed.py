import logging
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("successcore.feed")


async def get_activity_feed(db: AsyncSession, limit: int = 50) -> List[dict]:
    events: List[dict] = []

    try:
        result = await db.execute(
            text("SELECT id, user_id, action, details, created_at FROM audit_logs ORDER BY created_at DESC LIMIT :limit"),
            {"limit": limit}
        )
        for row in result:
            events.append({
                "id": row[0],
                "type": "audit",
                "user_id": row[1],
                "action": row[2],
                "details": row[3],
                "timestamp": row[4].isoformat() if row[4] else None,
            })
    except Exception as e:
        logger.debug(f"Audit feed error: {e}")

    try:
        from app.models.kudos import Kudos
        kudos_res = await db.execute(
            select(Kudos).order_by(Kudos.created_at.desc()).limit(limit)
        )
        for k in kudos_res.scalars().all():
            events.append({
                "id": k.id,
                "type": "kudos",
                "sender": k.sender_name,
                "receiver": k.receiver_name,
                "message": k.message,
                "timestamp": k.created_at.isoformat() if k.created_at else None,
            })
    except Exception:
        pass

    try:
        from app.models.user import User
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        users_res = await db.execute(
            select(User).where(User.created_at >= week_ago).order_by(User.created_at.desc()).limit(10)
        )
        for u in users_res.scalars().all():
            events.append({
                "id": f"newhire-{u.id}",
                "type": "new_hire",
                "name": u.full_name or u.email,
                "department": u.department,
                "timestamp": u.created_at.isoformat() if u.created_at else None,
            })
    except Exception:
        pass

    try:
        from app.models.agent import AgentExecutionRun
        runs_res = await db.execute(
            select(AgentExecutionRun).order_by(AgentExecutionRun.created_at.desc()).limit(10)
        )
        for r in runs_res.scalars().all():
            events.append({
                "id": f"agentrun-{r.id}",
                "type": "agent_run",
                "agent_id": r.agent_id,
                "status": r.status,
                "cost_usd": r.cost_usd,
                "timestamp": r.created_at.isoformat() if r.created_at else None,
            })
    except Exception:
        pass

    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return events[:limit]
