from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from app.api.dependencies import get_tenant_db, require_roles, get_current_user
from app.models.review_360 import DEFAULT_CATEGORIES

router = APIRouter()


class CreateCycleRequest(BaseModel):
    name: str
    description: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    categories: Optional[List[dict]] = None


class AssignReviewersRequest(BaseModel):
    subject_id: str
    reviewer_ids: List[str]
    relationship_type: str = "peer"
    is_anonymous: bool = True


class SubmitReviewRequest(BaseModel):
    overall_rating: float
    ratings: List[dict]
    strengths: str = ""
    improvements: str = ""
    comments: str = ""


@router.get("/categories")
async def get_review_categories():
    return {"categories": DEFAULT_CATEGORIES}


@router.post("/cycles", response_model=dict)
async def create_cycle(
    body: CreateCycleRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "super_admin"]))
):
    from app.services.review_360_service import create_review_cycle
    cycle = await create_review_cycle(
        db, name=body.name, description=body.description,
        start_date=body.start_date, end_date=body.end_date,
        created_by=current_user.get("sub", ""),
        categories=body.categories,
    )
    return {
        "id": cycle.id, "name": cycle.name, "status": cycle.status,
        "start_date": cycle.start_date.isoformat() if cycle.start_date else None,
        "end_date": cycle.end_date.isoformat() if cycle.end_date else None,
    }


@router.get("/cycles", response_model=dict)
async def list_cycles(db: AsyncSession = Depends(get_tenant_db)):
    from app.models.review_360 import ReviewCycle
    from sqlalchemy import select
    result = await db.execute(select(ReviewCycle).order_by(ReviewCycle.created_at.desc()))
    cycles = result.scalars().all()
    return {
        "cycles": [
            {
                "id": c.id, "name": c.name, "status": c.status,
                "review_type": c.review_type,
                "start_date": c.start_date.isoformat() if c.start_date else None,
                "end_date": c.end_date.isoformat() if c.end_date else None,
                "created_at": c.created_at.isoformat(),
            }
            for c in cycles
        ]
    }


@router.post("/cycles/{cycle_id}/assign", response_model=dict)
async def assign_reviewers(
    cycle_id: str,
    body: AssignReviewersRequest,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "super_admin"]))
):
    from app.services.review_360_service import assign_reviewers
    reviews = await assign_reviewers(db, cycle_id, body.subject_id, body.reviewer_ids, body.relationship_type, body.is_anonymous)
    return {"assigned_count": len(reviews), "review_ids": [r.id for r in reviews]}


@router.post("/reviews/{review_id}/submit", response_model=dict)
async def submit_review(
    review_id: str,
    body: SubmitReviewRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    from app.services.review_360_service import submit_review
    review = await submit_review(
        db, review_id, body.overall_rating, body.ratings,
        body.strengths, body.improvements, body.comments,
    )
    return {
        "review_id": review.id, "status": review.status,
        "overall_rating": review.overall_rating,
        "submitted_at": review.submitted_at.isoformat() if review.submitted_at else None,
    }


@router.get("/subjects/{subject_id}/feedback", response_model=dict)
async def get_subject_feedback(
    subject_id: str,
    cycle_id: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    from app.services.review_360_service import get_subject_feedback
    return await get_subject_feedback(db, subject_id, cycle_id)


@router.get("/cycles/{cycle_id}/progress", response_model=dict)
async def get_cycle_progress(cycle_id: str, db: AsyncSession = Depends(get_tenant_db)):
    from app.services.review_360_service import get_cycle_progress
    return await get_cycle_progress(db, cycle_id)


@router.get("/subjects/{subject_id}/summary", response_model=dict)
async def get_ai_feedback_summary(
    subject_id: str,
    cycle_id: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user)
):
    from app.services.review_360_service import generate_ai_summary
    summary = await generate_ai_summary(db, subject_id, cycle_id)
    return {"subject_id": subject_id, "summary": summary}
