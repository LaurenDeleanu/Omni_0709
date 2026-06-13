from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid

from app.api.dependencies import get_tenant_db, get_current_user, require_roles
from app.models.it import ITKnowledgeArticle, ITTicket

router = APIRouter()


class ArticleCreate(BaseModel):
    title: str
    problem_description: str
    root_cause: Optional[str] = None
    resolution_steps: list = []
    symptoms: list = []
    prevention_tips: list = []
    category: str = "general"
    tags: list = []


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    problem_description: Optional[str] = None
    root_cause: Optional[str] = None
    resolution_steps: Optional[list] = None
    symptoms: Optional[list] = None
    prevention_tips: Optional[list] = None
    category: Optional[str] = None
    tags: Optional[list] = None


class ArticleResponse(BaseModel):
    id: str
    title: str
    problem_description: Optional[str] = None
    symptoms: list = []
    root_cause: Optional[str] = None
    resolution_steps: list = []
    prevention_tips: list = []
    category: str
    tags: list = []
    source_ticket_id: Optional[str] = None
    author: Optional[str] = None
    view_count: int = 0
    helpful_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("/kb/articles", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(
    data: ArticleCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin", "it_manager"]))
):
    article = ITKnowledgeArticle(
        id=uuid.uuid4().hex,
        title=data.title,
        problem_description=data.problem_description,
        root_cause=data.root_cause,
        resolution_steps=data.resolution_steps,
        symptoms=data.symptoms,
        prevention_tips=data.prevention_tips,
        category=data.category,
        tags=data.tags,
        author=current_user.get("email", "unknown"),
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return article


@router.put("/kb/articles/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: str,
    data: ArticleUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin", "it_manager"]))
):
    result = await db.execute(select(ITKnowledgeArticle).where(ITKnowledgeArticle.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(article, key, value)

    await db.commit()
    await db.refresh(article)
    return article


@router.delete("/kb/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin", "it_manager"]))
):
    result = await db.execute(select(ITKnowledgeArticle).where(ITKnowledgeArticle.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    await db.delete(article)
    await db.commit()
    return None


@router.post("/kb/articles/{article_id}/helpful", response_model=dict)
async def mark_article_helpful(
    article_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    result = await db.execute(select(ITKnowledgeArticle).where(ITKnowledgeArticle.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    article.helpful_count = (article.helpful_count or 0) + 1
    await db.commit()
    return {"id": article_id, "helpful_count": article.helpful_count}


@router.get("/kb/tags", response_model=dict)
async def get_kb_tags(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "employee", "it_manager"]))
):
    result = await db.execute(select(ITKnowledgeArticle.tags, ITKnowledgeArticle.category))
    articles = result.all()

    tags_count = {}
    categories = set()
    for tags, category in articles:
        if category:
            categories.add(category)
        if tags:
            for tag in tags:
                tags_count[tag] = tags_count.get(tag, 0) + 1

    sorted_tags = sorted(tags_count.items(), key=lambda x: -x[1])[:30]
    return {
        "tags": [{"name": name, "count": count} for name, count in sorted_tags],
        "categories": sorted(list(categories)),
    }


@router.get("/kb-suggest/{ticket_id}", response_model=dict)
async def get_kb_suggestions_for_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "employee", "it_manager"]))
):
    ticket_result = await db.execute(select(ITTicket).where(ITTicket.id == ticket_id))
    ticket = ticket_result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    from app.services.it_knowledge_base import suggest_solutions
    suggested_ids = await suggest_solutions(ticket_id, db)

    articles = []
    if suggested_ids:
        result = await db.execute(
            select(ITKnowledgeArticle).where(ITKnowledgeArticle.id.in_(suggested_ids)).limit(5)
        )
        articles = result.scalars().all()

    return {
        "ticket_id": ticket_id,
        "suggestions": [
            {
                "id": a.id,
                "title": a.title,
                "category": a.category,
                "helpful_count": a.helpful_count or 0,
                "view_count": a.view_count or 0,
            }
            for a in articles
        ]
    }
