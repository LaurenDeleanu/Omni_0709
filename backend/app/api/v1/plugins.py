from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional

from app.api.dependencies import get_tenant_db, require_roles, get_current_user

router = APIRouter()


class PluginCreate(BaseModel):
    name: str; version: str = "1.0.0"; author: str; author_email: str = ""
    description: str; category: str = "tools"; icon: str = "🧩"
    manifest: dict = {}; source_code_url: str = ""


class PluginReviewIn(BaseModel):
    rating: int; review: str = ""


class PluginInstallIn(BaseModel):
    config: dict = {}


async def _recalc_avg_rating(db: AsyncSession, plugin_id: str):
    from app.models.plugin import PluginReview, Plugin
    result = await db.execute(select(func.avg(PluginReview.rating)).where(PluginReview.plugin_id == plugin_id))
    avg = result.scalar() or 0
    p = (await db.execute(select(Plugin).where(Plugin.id == plugin_id))).scalar_one_or_none()
    if p:
        p.avg_rating = round(float(avg), 2)
        await db.commit()


@router.get("")
async def list_plugins(category: str = Query(""), search: str = Query(""), db: AsyncSession = Depends(get_tenant_db)):
    from app.models.plugin import Plugin
    stmt = select(Plugin).where(Plugin.is_published == True).order_by(Plugin.install_count.desc())
    if category:
        stmt = stmt.where(Plugin.category == category)
    if search:
        stmt = stmt.where(Plugin.name.ilike(f"%{search}%") | Plugin.description.ilike(f"%{search}%"))
    result = await db.execute(stmt.limit(50))
    plugins = result.scalars().all()
    return {"plugins": [{"id": p.id, "name": p.name, "version": p.version, "author": p.author, "description": p.description, "category": p.category, "icon": p.icon, "install_count": p.install_count, "avg_rating": p.avg_rating, "is_verified": p.is_verified} for p in plugins], "categories": ["tools", "hr", "communication", "analytics", "compliance", "productivity"]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def register_plugin(body: PluginCreate, db: AsyncSession = Depends(get_tenant_db), current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))):
    from app.models.plugin import Plugin
    import uuid
    existing = await db.execute(select(Plugin).where(Plugin.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Plugin name already taken")
    plugin = Plugin(id=uuid.uuid4().hex, **body.model_dump())
    db.add(plugin)
    await db.commit()
    await db.refresh(plugin)
    return {"id": plugin.id, "name": plugin.name, "status": "registered"}


@router.post("/{plugin_id}/install")
async def install_plugin(plugin_id: str, body: PluginInstallIn, db: AsyncSession = Depends(get_tenant_db), current_user: dict = Depends(require_roles(["hr_admin", "sys_admin"]))):
    from app.models.plugin import Plugin, PluginInstall
    import uuid
    p = (await db.execute(select(Plugin).where(Plugin.id == plugin_id, Plugin.is_published == True))).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Plugin not found")
    existing = await db.execute(select(PluginInstall).where(PluginInstall.plugin_id == plugin_id, PluginInstall.tenant_id == "acme_corp"))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already installed")
    install = PluginInstall(id=uuid.uuid4().hex, plugin_id=plugin_id, tenant_id="acme_corp", config=body.config)
    db.add(install)
    p.install_count += 1
    await db.commit()
    return {"status": "installed", "plugin_id": plugin_id}


@router.post("/{plugin_id}/uninstall")
async def uninstall_plugin(plugin_id: str, db: AsyncSession = Depends(get_tenant_db), _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))):
    from app.models.plugin import Plugin, PluginInstall
    result = await db.execute(select(PluginInstall).where(PluginInstall.plugin_id == plugin_id, PluginInstall.tenant_id == "acme_corp"))
    install = result.scalar_one_or_none()
    if not install:
        raise HTTPException(status_code=404, detail="Install not found")
    await db.delete(install)
    p = (await db.execute(select(Plugin).where(Plugin.id == plugin_id))).scalar_one_or_none()
    if p:
        p.install_count = max(0, p.install_count - 1)
    await db.commit()
    return {"status": "uninstalled"}


@router.get("/installed")
async def list_installed(db: AsyncSession = Depends(get_tenant_db), _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))):
    from app.models.plugin import Plugin, PluginInstall
    result = await db.execute(select(PluginInstall).where(PluginInstall.tenant_id == "acme_corp", PluginInstall.enabled == True))
    installs = result.scalars().all()
    plugin_ids = [i.plugin_id for i in installs]
    result2 = await db.execute(select(Plugin).where(Plugin.id.in_(plugin_ids)))
    plugins = result2.scalars().all()
    return {"installed": [{"id": p.id, "name": p.name, "icon": p.icon, "manifest": p.manifest} for p in plugins]}


@router.get("/{plugin_id}/reviews")
async def get_reviews(plugin_id: str, db: AsyncSession = Depends(get_tenant_db)):
    from app.models.plugin import PluginReview
    result = await db.execute(select(PluginReview).where(PluginReview.plugin_id == plugin_id).order_by(PluginReview.created_at.desc()).limit(50))
    reviews = result.scalars().all()
    return {"reviews": [{"id": r.id, "user_name": r.user_name, "rating": r.rating, "review": r.review, "created_at": r.created_at.isoformat()} for r in reviews]}


@router.post("/{plugin_id}/reviews", status_code=status.HTTP_201_CREATED)
async def add_review(plugin_id: str, body: PluginReviewIn, db: AsyncSession = Depends(get_tenant_db), current_user: dict = Depends(get_current_user)):
    from app.models.plugin import PluginReview, Plugin
    import uuid
    p = (await db.execute(select(Plugin).where(Plugin.id == plugin_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Plugin not found")
    if body.rating < 1 or body.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")
    user_id = current_user.get("sub", "").split("|")[-1]
    user_name = current_user.get("email", "unknown")
    review = PluginReview(id=uuid.uuid4().hex, plugin_id=plugin_id, user_id=user_id, user_name=user_name, rating=body.rating, review=body.review)
    db.add(review)
    await db.commit()
    await _recalc_avg_rating(db, plugin_id)
    return {"status": "reviewed", "rating": body.rating}


@router.patch("/{plugin_id}/publish")
async def publish_plugin(plugin_id: str, db: AsyncSession = Depends(get_tenant_db), _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))):
    from app.models.plugin import Plugin
    p = (await db.execute(select(Plugin).where(Plugin.id == plugin_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Plugin not found")
    p.is_published = True; p.is_verified = True
    await db.commit()
    return {"status": "published"}


@router.delete("/{plugin_id}")
async def delete_plugin(plugin_id: str, db: AsyncSession = Depends(get_tenant_db), _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))):
    from app.models.plugin import Plugin
    p = (await db.execute(select(Plugin).where(Plugin.id == plugin_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Plugin not found")
    await db.delete(p)
    await db.commit()
    return {"status": "deleted"}
