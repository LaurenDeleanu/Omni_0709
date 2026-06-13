import logging
from typing import Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("successcore.digest")


async def generate_notification_digest(db: AsyncSession) -> dict:
    from app.models.notification import Notification
    from app.models.kudos import Kudos
    from app.models.user import User
    from app.models.agent import AgentExecutionRun

    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    unread_notifs_res = await db.execute(
        select(Notification).where(Notification.is_read == False).order_by(Notification.created_at.desc()).limit(20)
    )
    unread_notifs = unread_notifs_res.scalars().all()

    kudos_res = await db.execute(
        select(Kudos).where(Kudos.created_at >= yesterday).order_by(Kudos.created_at.desc()).limit(10)
    )
    recent_kudos = kudos_res.scalars().all()

    new_users_res = await db.execute(
        select(User).where(User.created_at >= week_ago).order_by(User.created_at.desc())
    )
    new_users = new_users_res.scalars().all()

    agent_runs_res = await db.execute(
        select(AgentExecutionRun).where(AgentExecutionRun.created_at >= yesterday).order_by(AgentExecutionRun.created_at.desc()).limit(10)
    )
    agent_runs = agent_runs_res.scalars().all()

    summary = f"Daily Digest — {now.strftime('%Y-%m-%d')}\n\n"
    summary += f"Unread notifications: {len(unread_notifs)}\n"
    summary += f"Kudos given today: {len(recent_kudos)}\n"
    summary += f"New hires this week: {len(new_users)}\n"
    summary += f"Agent runs today: {len(agent_runs)}\n\n"

    notif_items = []
    for n in unread_notifs[:10]:
        notif_items.append({
            "id": n.id,
            "title": n.title,
            "message": n.message[:200],
            "type": n.type,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        })

    kudos_items = []
    for k in recent_kudos:
        kudos_items.append({
            "from": k.sender_name,
            "to": k.receiver_name,
            "message": k.message[:200],
        })

    agent_items = []
    for r in agent_runs:
        agent_items.append({
            "agent_id": r.agent_id,
            "status": r.status,
            "cost_usd": r.cost_usd,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return {
        "summary": summary,
        "stats": {
            "unread_notifications": len(unread_notifs),
            "kudos_today": len(recent_kudos),
            "new_hires_week": len(new_users),
            "agent_runs_today": len(agent_runs),
        },
        "notifications": notif_items,
        "recent_kudos": kudos_items,
        "agent_runs": agent_items,
    }
