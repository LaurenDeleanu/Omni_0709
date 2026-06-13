from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.dependencies import get_tenant_db, require_roles
from app.models.announcement import Announcement
from typing import List
from pydantic import BaseModel
from datetime import datetime
import uuid

router = APIRouter()

class AnnouncementCreate(BaseModel):
    title: str
    content: str

class AnnouncementOut(BaseModel):
    id: str
    title: str
    content: str
    author_id: str | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

def get_user_id(current_user: dict) -> str:
    sub = current_user.get("sub", "")
    return sub.split("|")[-1] if "|" in sub else sub

@router.get("", response_model=List[AnnouncementOut])
async def get_announcements(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    """Obtener todos los anuncios activos."""
    result = await db.execute(
        select(Announcement)
        .where(Announcement.is_active == True)
        .order_by(Announcement.created_at.desc())
    )
    return result.scalars().all()

@router.post("", response_model=AnnouncementOut, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    announcement_in: AnnouncementCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """Crear un nuevo anuncio de la compañía (Solo HR/Sys Admin)."""
    user_id = get_user_id(current_user)
    announcement = Announcement(
        id=uuid.uuid4().hex,
        title=announcement_in.title,
        content=announcement_in.content,
        author_id=user_id,
        is_active=True
    )
    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)
    return announcement

@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    announcement_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    """Eliminar un anuncio (Solo HR/Sys Admin)."""
    result = await db.execute(select(Announcement).where(Announcement.id == announcement_id))
    announcement = result.scalar_one_or_none()
    if not announcement:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")
    
    await db.delete(announcement)
    await db.commit()
    return None
