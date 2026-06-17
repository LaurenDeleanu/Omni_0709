from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.api.dependencies import get_tenant_db, get_current_user, require_roles
from app.api.v1._pagination import paginate_query
from app.schemas.pagination import PaginatedResponse
from app.models.notification import Notification
from app.services.ws_notifications import connect_notifications, disconnect_notifications, push_notification_to_user
from app.services.broadcast import broadcast_notification
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


@router.websocket("/ws")
async def notification_websocket(
    ws: WebSocket,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("sub", "").split("|")[-1]
    await connect_notifications(user_id, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        disconnect_notifications(user_id, ws)
    except Exception:
        disconnect_notifications(user_id, ws)


class BroadcastIn(BaseModel):
    title: str
    message: str
    department: Optional[str] = None
    role: Optional[str] = None
    type: str = "broadcast"


@router.post("/broadcast", status_code=status.HTTP_201_CREATED)
async def broadcast_notification_endpoint(
    body: BroadcastIn,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    return await broadcast_notification(db, body.title, body.message, body.type, body.department, body.role)

def get_user_id(current_user: dict) -> str:
    sub = current_user.get("sub", "")
    return sub.split("|")[-1] if "|" in sub else sub

class NotificationOut(BaseModel):
    id: str
    user_id: str
    title: str
    message: str
    type: str
    is_read: bool
    link: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("", response_model=List[NotificationOut])
async def get_my_notifications(
    page: Optional[int] = Query(None, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = get_user_id(current_user)
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
    )

    limit = page_size if page_size else 50
    offset = ((page or 1) - 1) * limit
    stmt = stmt.limit(limit).offset(offset)

    exec_result = await db.execute(stmt)
    return exec_result.scalars().all()

@router.post("/read-all", status_code=status.HTTP_200_OK)
async def read_all_notifications(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    """Marcar todas las notificaciones del usuario como leídas."""
    user_id = get_user_id(current_user)
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return {"message": "Todas las notificaciones marcadas como leídas."}

@router.post("/{notification_id}/read", response_model=NotificationOut)
async def read_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    """Marcar una notificación específica como leída."""
    user_id = get_user_id(current_user)
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return notification


class PushSubscriptionIn(BaseModel):
    endpoint: str
    keys: dict

@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe_push(
    sub_in: PushSubscriptionIn,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    from app.models.push import PushSubscription
    from app.services.push_service import add_subscription
    import uuid

    user_id = get_user_id(current_user)
    
    # Check if exists
    result = await db.execute(
        select(PushSubscription).where(PushSubscription.endpoint == sub_in.endpoint)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.user_id = user_id
        existing.keys = sub_in.keys
    else:
        new_sub = PushSubscription(
            id=uuid.uuid4().hex,
            user_id=user_id,
            endpoint=sub_in.endpoint,
            keys=sub_in.keys
        )
        db.add(new_sub)

    await db.commit()
    add_subscription({"endpoint": sub_in.endpoint, "keys": sub_in.keys, "user_id": user_id})
    return {"message": "Suscripción guardada exitosamente"}

async def send_web_push(db: AsyncSession, user_id: str, payload: dict):
    from app.models.push import PushSubscription
    from pywebpush import webpush, WebPushException
    import json
    import os
    
    result = await db.execute(select(PushSubscription).where(PushSubscription.user_id == user_id))
    subs = result.scalars().all()
    
    private_key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "private_key.pem")
    
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": sub.keys
                },
                data=json.dumps(payload),
                vapid_private_key=private_key_path,
                vapid_claims={
                    "sub": "mailto:admin@successcore.com"
                }
            )
        except WebPushException as e:
            # If expired, we could delete the subscription
            if e.response and e.response.status_code in [404, 410]:
                await db.delete(sub)
            print(f"Web Push Error: {e}")
            
    await db.commit()
