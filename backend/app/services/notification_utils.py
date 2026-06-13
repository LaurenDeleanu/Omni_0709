import logging
import uuid
import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("successcore.notification_utils")


async def create_and_push_notification(
    db: AsyncSession,
    user_id: str,
    title: str,
    message: str,
    type_: str = "system",
    link: str = None,
) -> dict:
    from app.models.notification import Notification

    notif = Notification(
        id=uuid.uuid4().hex,
        user_id=user_id,
        title=title,
        message=message,
        type=type_,
        link=link,
    )
    db.add(notif)
    await db.flush()

    asyncio.create_task(_push_via_ws(user_id, notif))

    return {
        "id": notif.id,
        "user_id": user_id,
        "title": title,
        "message": message[:100],
        "type": type_,
    }


async def _push_via_ws(user_id: str, notif):
    try:
        from app.services.ws_notifications import push_notification_to_user
        sent = await push_notification_to_user(user_id, {
            "id": notif.id,
            "title": notif.title,
            "message": notif.message,
            "type": notif.type,
            "link": getattr(notif, "link", None),
            "created_at": notif.created_at.isoformat() if notif.created_at else None,
        })
        if sent:
            logger.debug(f"WS push: sent notification to {user_id}")
    except Exception as e:
        logger.debug(f"WS push skipped: {e}")
