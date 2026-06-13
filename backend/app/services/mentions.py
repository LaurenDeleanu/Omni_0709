import re
import logging
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.notification import Notification
from app.services.notification_utils import create_and_push_notification

logger = logging.getLogger("successcore.mentions")

MENTION_RE = re.compile(r"@([a-zA-Z0-9._%+\-]+)")


def extract_mentions(text: str) -> List[str]:
    if not text:
        return []
    return list(set(MENTION_RE.findall(text)))


async def resolve_mentions(db: AsyncSession, text: str) -> List[Tuple[str, str]]:
    patterns = extract_mentions(text)
    if not patterns:
        return []

    results = []
    for pattern in patterns:
        user = await db.execute(
            select(User).where(
                (User.email == pattern) | (User.full_name.ilike(f"%{pattern}%"))
            )
        )
        found = user.scalar_one_or_none()
        if found:
            results.append((pattern, found.id))
    return results


async def notify_mentioned_users(
    db: AsyncSession,
    text: str,
    sender_id: str,
    sender_name: str,
    entity_type: str,
    entity_id: str,
) -> int:
    mentions = await resolve_mentions(db, text)
    if not mentions:
        return 0

    notified = 0
    for pattern, user_id in mentions:
        if user_id == sender_id:
            continue
        await create_and_push_notification(
            db, user_id,
            title=f"@{sender_name} te ha mencionado",
            message=f"En {entity_type} ({entity_id}): {text[:200]}",
            type_="mention",
        )
        notified += 1

    if notified:
        await db.flush()
    return notified
