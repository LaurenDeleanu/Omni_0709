import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("successcore.email_digest")

async def send_daily_digest(db: AsyncSession, admin_email: str) -> dict:
    from app.services.digest_service import generate_notification_digest

    digest = await generate_notification_digest(db)
    summary = digest.get("summary", "")
    stats = digest.get("stats", {})

    subject = f"SuccessCore Daily Digest — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    body = (
        f"<h2>Daily Digest</h2>"
        f"<p>{summary.replace(chr(10), '<br>')}</p>"
        f"<h3>Stats</h3>"
        f"<ul>"
        f"<li>Unread notifications: {stats.get('unread_notifications', 0)}</li>"
        f"<li>Kudos today: {stats.get('kudos_today', 0)}</li>"
        f"<li>New hires this week: {stats.get('new_hires_week', 0)}</li>"
        f"<li>Agent runs today: {stats.get('agent_runs_today', 0)}</li>"
        f"</ul>"
    )

    try:
        from app.services.email_service import send_email
        sent = await send_email(admin_email, subject, body, html=True)
        return {"sent": sent, "to": admin_email, "stats": stats}
    except Exception as e:
        logger.error(f"Digest email failed: {e}")
        return {"sent": False, "error": str(e)}
