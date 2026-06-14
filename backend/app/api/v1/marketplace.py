"""
marketplace.py — Agent marketplace API. Publish, browse, install AI agents.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, distinct
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime, timezone

from app.api.dependencies import get_tenant_db, get_current_user, require_roles

router = APIRouter(prefix="/marketplace", tags=["Agent Marketplace"])


class MarketplaceAgent(BaseModel):
    id: str
    name: str
    description: str
    agent_type: str
    category: str
    author: str
    author_tenant: str
    price: float = 0
    rating: float = 0
    downloads: int = 0
    tags: list[str] = []
    preview_image: str = ""
    created_at: str = ""


@router.get("/agents")
async def list_marketplace_agents(
    search: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    sort: str = Query(default="popular", regex="^(popular|newest|rating|price)$"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Browse marketplace agents with search, filtering, and sorting."""
    from app.models.agent import Agent

    query = select(Agent).where(Agent.is_published == True)

    if search:
        query = query.where(
            or_(
                Agent.name.ilike(f"%{search}%"),
                Agent.description.ilike(f"%{search}%"),
            )
        )
    if category:
        query = query.where(Agent.marketplace_category == category)

    if sort == "popular":
        query = query.order_by(Agent.marketplace_downloads.desc())
    elif sort == "newest":
        query = query.order_by(Agent.marketplace_published_at.desc())
    elif sort == "rating":
        query = query.order_by(Agent.marketplace_rating.desc())

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    agents = result.scalars().all()

    return {
        "agents": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description or "",
                "agent_type": a.agent_type,
                "category": a.marketplace_category or "general",
                "author": a.marketplace_author or "Unknown",
                "author_tenant": a.marketplace_author_tenant or "",
                "price": a.marketplace_price or 0,
                "rating": round(a.marketplace_rating or 0, 1),
                "downloads": a.marketplace_downloads or 0,
                "tags": a.marketplace_tags or [],
                "preview_image": a.marketplace_preview_image or "",
                "created_at": a.marketplace_published_at.isoformat() if a.marketplace_published_at else "",
            }
            for a in agents
        ],
        "total": total,
        "page": page,
        "pages": max(1, (total + limit - 1) // limit),
    }


@router.get("/agents/{agent_id}")
async def get_marketplace_agent_detail(
    agent_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Get detailed view of a marketplace agent."""
    from app.models.agent import Agent
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description or "",
        "agent_type": agent.agent_type,
        "system_prompt": agent.system_prompt or "",
        "category": agent.marketplace_category or "general",
        "author": agent.marketplace_author or "Unknown",
        "price": agent.marketplace_price or 0,
        "rating": round(agent.marketplace_rating or 0, 1),
        "downloads": agent.marketplace_downloads or 0,
        "tags": agent.marketplace_tags or [],
        "tools": agent.marketplace_tools or [],
        "created_at": agent.marketplace_published_at.isoformat() if agent.marketplace_published_at else "",
        "is_published": agent.is_published or False,
    }


class PublishRequest(BaseModel):
    name: str = ""
    description: str = ""
    category: str = "general"
    price: float = 0
    tags: list[str] = []
    preview_image: str = ""


@router.post("/agents/{agent_id}/publish")
async def publish_agent(
    agent_id: str,
    body: PublishRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "super_admin", "manager"])),
):
    """Publish an agent to the marketplace."""
    from app.models.agent import Agent
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.is_published = True
    agent.marketplace_published_at = datetime.now(timezone.utc)
    agent.marketplace_category = body.category
    agent.marketplace_price = body.price
    agent.marketplace_tags = body.tags or []
    agent.marketplace_preview_image = body.preview_image
    agent.marketplace_author = current_user.get("name", current_user.get("email", "Anonymous"))
    agent.marketplace_author_tenant = current_user.get("tenant_id", "")

    if body.name:
        agent.name = body.name
    if body.description:
        agent.description = body.description

    await db.commit()
    return {"status": "published", "agent_id": agent_id}


@router.post("/agents/{agent_id}/install")
async def install_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Install (clone) a marketplace agent into the current tenant."""
    from app.models.agent import Agent
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Clone the agent for the current tenant
    new_id = uuid.uuid4().hex
    clone = Agent(
        id=new_id,
        name=f"{original.name} (Installed)",
        description=original.description,
        agent_type=original.agent_type,
        system_prompt=original.system_prompt,
        tenant_id=current_user.get("tenant_id", "default"),
        is_published=False,
    )
    db.add(clone)
    original.marketplace_downloads = (original.marketplace_downloads or 0) + 1
    await db.commit()

    return {"status": "installed", "new_agent_id": new_id, "original_id": agent_id}


@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_tenant_db)):
    """List available marketplace categories."""
    from app.models.agent import Agent
    from sqlalchemy import distinct
    result = await db.execute(
        select(distinct(Agent.marketplace_category)).where(Agent.is_published == True)
    )
    categories = [c[0] for c in result.all() if c[0]]
    default_categories = ["customer-support", "sales", "hr", "it", "finance", "legal", "general"]
    return {"categories": list(set(default_categories + categories))}
