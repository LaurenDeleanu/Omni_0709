import logging
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger("successcore.broadcast")


async def broadcast_notification(
    db: AsyncSession,
    title: str,
    message: str,
    type_: str = "broadcast",
    department: Optional[str] = None,
    role: Optional[str] = None,
    link: Optional[str] = None,
) -> dict:
    from app.models.user import User
    from app.services.notification_utils import create_and_push_notification

    stmt = select(User).where(User.is_active == True)
    if department:
        stmt = stmt.where(User.department == department)
    if role:
        stmt = stmt.where(User.role == role)

    result = await db.execute(stmt)
    users = result.scalars().all()

    sent = 0
    for user in users:
        await create_and_push_notification(db, user.id, title, message, type_, link=link)
        sent += 1

    await db.commit()
    logger.info(f"Broadcast notification sent to {sent} users: {title}")
    return {
        "title": title,
        "message": message,
        "sent_to": sent,
        "department": department,
        "role": role,
    }
