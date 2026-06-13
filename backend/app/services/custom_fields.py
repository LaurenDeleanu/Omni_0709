import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger("successcore.customfields")


async def set_custom_field(db: AsyncSession, user_id: str, field_name: str, value: Any) -> dict:
    from app.models.user import User
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")

    if not hasattr(user, 'custom_fields'):
        return {"error": "custom_fields column not yet added to database. Run Alembic migration."}

    current = dict(user.custom_fields) if user.custom_fields else {}
    current[field_name] = value
    user.custom_fields = current
    await db.commit()
    return {"user_id": user_id, "field": field_name, "value": value}


async def delete_custom_field(db: AsyncSession, user_id: str, field_name: str) -> dict:
    from app.models.user import User
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")

    if not hasattr(user, 'custom_fields'):
        return {"error": "custom_fields column not yet added to database. Run Alembic migration."}

    current = dict(user.custom_fields) if user.custom_fields else {}
    removed = current.pop(field_name, None)
    user.custom_fields = current
    await db.commit()
    return {"user_id": user_id, "field": field_name, "removed": removed is not None}
