from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import List, Optional

from app.api.dependencies import get_tenant_db, get_current_user, require_roles

router = APIRouter()


class NotificationPrefsIn(BaseModel):
    email_notifications: bool = True
    push_notifications: bool = True
    in_app_notifications: bool = True
    digest_frequency: str = "daily"
    muted_until: Optional[str] = None


class NotificationPrefsOut(BaseModel):
    email_notifications: bool
    push_notifications: bool
    in_app_notifications: bool
    digest_frequency: str
    muted_until: Optional[str] = None


_notification_prefs: dict = {}


def _get_prefs(user_id: str) -> dict:
    if user_id not in _notification_prefs:
        _notification_prefs[user_id] = {
            "email_notifications": True, "push_notifications": True,
            "in_app_notifications": True, "digest_frequency": "daily", "muted_until": None,
        }
    return _notification_prefs[user_id]


@router.get("/preferences", response_model=NotificationPrefsOut)
async def get_notification_preferences(
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user.get("sub", "").split("|")[-1]
    return _get_prefs(user_id)


@router.put("/preferences", response_model=NotificationPrefsOut)
async def update_notification_preferences(
    prefs: NotificationPrefsIn,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user.get("sub", "").split("|")[-1]
    current = _get_prefs(user_id)
    for key, value in prefs.model_dump(exclude_unset=True).items():
        current[key] = value
    _notification_prefs[user_id] = current
    return current


@router.get("/admin/all")
async def get_all_preferences(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    from app.models.notification_prefs import NotificationPrefs
    result = await db.execute(select(NotificationPrefs).order_by(NotificationPrefs.user_id.asc()))
    prefs = result.scalars().all()
    return {"count": len(prefs), "preferences": [
        {"user_id": p.user_id, "email": p.email_notifications, "push": p.push_notifications,
         "in_app": p.in_app_notifications, "digest": p.digest_frequency, "muted": p.muted_until.isoformat() if p.muted_until else None}
        for p in prefs
    ]}
