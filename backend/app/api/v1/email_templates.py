from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional

from app.api.dependencies import get_tenant_db, require_roles
from app.models.email_template import EmailTemplate

router = APIRouter()


class EmailTemplateIn(BaseModel):
    name: str
    subject: str
    body_html: str
    is_default: bool = False


class EmailTemplateOut(BaseModel):
    id: str
    name: str
    subject: str
    body_html: str
    is_default: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[EmailTemplateOut])
async def list_templates(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    result = await db.execute(select(EmailTemplate).order_by(EmailTemplate.name.asc()))
    templates = result.scalars().all()
    return [
        EmailTemplateOut(
            id=t.id, name=t.name, subject=t.subject, body_html=t.body_html,
            is_default=t.is_default, created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat()
        ) for t in templates
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_template(
    body: EmailTemplateIn,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    import uuid
    t = EmailTemplate(id=uuid.uuid4().hex, tenant_id="acme_corp", **body.model_dump())
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return {"id": t.id, "name": t.name, "created": True}


@router.put("/{template_id}")
async def update_template(
    template_id: str,
    body: EmailTemplateIn,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    result = await db.execute(select(EmailTemplate).where(EmailTemplate.id == template_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(t, key, value)
    await db.commit()
    return {"id": t.id, "name": t.name, "updated": True}


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    result = await db.execute(select(EmailTemplate).where(EmailTemplate.id == template_id))
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.delete(t)
    await db.commit()
    return {"status": "deleted"}
