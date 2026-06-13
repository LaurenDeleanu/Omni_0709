from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.dependencies import get_tenant_db, get_current_user
from app.models.kudos import Kudos
from app.models.user import User
from app.models.notification import Notification
from app.services.notification_utils import create_and_push_notification
from app.services.event_publisher import publish_kudos_event
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

router = APIRouter()

class KudosCreate(BaseModel):
    receiver_id: str
    message: str
    badge: str

class UserMini(BaseModel):
    id: str
    full_name: str | None
    email: str

    class Config:
        from_attributes = True

class KudosOut(BaseModel):
    id: str
    sender_id: str
    sender: UserMini | None = None
    receiver_id: str
    receiver: UserMini | None = None
    message: str
    badge: str
    created_at: datetime

    class Config:
        from_attributes = True

def get_user_id(current_user: dict) -> str:
    sub = current_user.get("sub", "")
    return sub.split("|")[-1] if "|" in sub else sub

@router.get("", response_model=List[KudosOut])
async def get_kudos_feed(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtener el feed global de Kudos de la compañía."""
    result = await db.execute(
        select(Kudos)
        .order_by(Kudos.created_at.desc())
    )
    kudos_list = result.scalars().all()
    
    # We populate sender and receiver models dynamically
    populated_kudos = []
    for k in kudos_list:
        sender_res = await db.execute(select(User).where(User.id == k.sender_id))
        sender = sender_res.scalar_one_or_none()
        
        receiver_res = await db.execute(select(User).where(User.id == k.receiver_id))
        receiver = receiver_res.scalar_one_or_none()
        
        populated_kudos.append(
            KudosOut(
                id=k.id,
                sender_id=k.sender_id,
                sender=UserMini.model_validate(sender) if sender else None,
                receiver_id=k.receiver_id,
                receiver=UserMini.model_validate(receiver) if receiver else None,
                message=k.message,
                badge=k.badge,
                created_at=k.created_at
            )
        )
    return populated_kudos

@router.post("", response_model=KudosOut, status_code=status.HTTP_201_CREATED)
async def create_kudos(
    kudos_in: KudosCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    """Enviar un Kudos de reconocimiento a un compañero."""
    sender_id = get_user_id(current_user)
    
    if sender_id == kudos_in.receiver_id:
        raise HTTPException(status_code=400, detail="No puedes enviarte un Kudos a ti mismo.")
        
    # Verificar que el receptor exista
    receiver_res = await db.execute(select(User).where(User.id == kudos_in.receiver_id))
    receiver = receiver_res.scalar_one_or_none()
    if not receiver:
        raise HTTPException(status_code=404, detail="Usuario receptor no encontrado.")
        
    # Obtener info del remitente
    sender_res = await db.execute(select(User).where(User.id == sender_id))
    sender = sender_res.scalar_one_or_none()
    sender_name = sender.full_name if sender and sender.full_name else (sender.email if sender else "Un compañero")
    
    kudos = Kudos(
        id=uuid.uuid4().hex,
        sender_id=sender_id,
        receiver_id=kudos_in.receiver_id,
        message=kudos_in.message,
        badge=kudos_in.badge
    )
    db.add(kudos)

    await create_and_push_notification(
        db, kudos_in.receiver_id,
        title="🎉 ¡Has recibido un Kudos!",
        message=f"{sender_name} te ha enviado un Kudos de '{kudos_in.badge}': \"{kudos_in.message}\"",
        type_="kudos",
    )
    try:
        await publish_kudos_event(db, str(uuid.uuid4().hex[:12]), sender_id, kudos_in.receiver_id, kudos_in.badge, kudos_in.message, "acme_corp")
    except Exception:
        pass

    await db.commit()
    await db.refresh(kudos)
    
    return KudosOut(
        id=kudos.id,
        sender_id=kudos.sender_id,
        sender=UserMini.model_validate(sender) if sender else None,
        receiver_id=kudos.receiver_id,
        receiver=UserMini.model_validate(receiver) if receiver else None,
        message=kudos.message,
        badge=kudos.badge,
        created_at=kudos.created_at
    )
