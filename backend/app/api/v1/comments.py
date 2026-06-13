from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel

from app.api.dependencies import get_tenant_db, get_current_user, require_roles
from app.models.comment import Comment
from app.services.mentions import notify_mentioned_users, extract_mentions
import uuid

router = APIRouter()


class CommentCreate(BaseModel):
    entity_type: str
    entity_id: str
    content: str
    parent_id: Optional[str] = None


class CommentOut(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    parent_id: Optional[str] = None
    author_id: str
    author_name: str
    content: str
    is_resolved: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CommentThread(BaseModel):
    comment: CommentOut
    replies: List[CommentOut]


@router.get("", response_model=List[CommentThread])
async def get_comments(
    entity_type: str = Query(...),
    entity_id: str = Query(...),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["employee", "hr_admin", "sys_admin"]))
):
    result = await db.execute(
        select(Comment).where(
            Comment.entity_type == entity_type,
            Comment.entity_id == entity_id,
            Comment.parent_id == None,
        ).order_by(Comment.created_at.asc())
    )
    parents = result.scalars().all()

    threads = []
    for p in parents:
        child_result = await db.execute(
            select(Comment).where(Comment.parent_id == p.id).order_by(Comment.created_at.asc())
        )
        children = child_result.scalars().all()
        threads.append(CommentThread(
            comment=_comment_to_out(p),
            replies=[_comment_to_out(c) for c in children],
        ))
    return threads


@router.post("", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def create_comment(
    body: CommentCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user.get("sub", "").split("|")[-1]
    user_name = current_user.get("email", "unknown")

    comment = Comment(
        id=uuid.uuid4().hex,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        parent_id=body.parent_id,
        author_id=user_id,
        author_name=user_name,
        content=body.content,
    )
    db.add(comment)
    await db.flush()

    if body.content:
        await notify_mentioned_users(
            db, body.content,
            sender_id=user_id,
            sender_name=user_name,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
        )

    await db.commit()
    await db.refresh(comment)
    return _comment_to_out(comment)


@router.patch("/{comment_id}/resolve")
async def resolve_comment(
    comment_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "sys_admin"]))
):
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.is_resolved = True
    await db.commit()
    return {"status": "resolved"}


@router.get("/mentions/preview")
async def preview_mentions(
    text: str = Query(...),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(get_current_user),
):
    from app.services.mentions import resolve_mentions
    mentions = await resolve_mentions(db, text)
    return {"found": len(mentions), "matches": [{"pattern": m[0], "user_id": m[1]} for m in mentions]}


def _comment_to_out(c: Comment) -> CommentOut:
    return CommentOut(
        id=c.id,
        entity_type=c.entity_type,
        entity_id=c.entity_id,
        parent_id=c.parent_id,
        author_id=c.author_id,
        author_name=c.author_name,
        content=c.content,
        is_resolved=c.is_resolved,
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat() if c.updated_at else "",
    )
