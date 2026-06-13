import logging
import uuid
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.review_360 import ReviewCycle, Review, ReviewRating, DEFAULT_CATEGORIES

logger = logging.getLogger("successcore.review360")


async def create_review_cycle(
    db: AsyncSession,
    name: str,
    description: str = "",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    created_by: str = "",
    categories: Optional[List[Dict]] = None,
) -> ReviewCycle:
    cycle = ReviewCycle(
        id=uuid.uuid4().hex,
        name=name,
        description=description,
        status="draft",
        review_type="360",
        created_by=created_by,
        config={"categories": categories or DEFAULT_CATEGORIES},
    )
    if start_date:
        cycle.start_date = datetime.fromisoformat(start_date)
    if end_date:
        cycle.end_date = datetime.fromisoformat(end_date)
    db.add(cycle)
    await db.commit()
    await db.refresh(cycle)
    logger.info(f"Review cycle created: {cycle.name} ({cycle.id[:8]})")
    return cycle


async def assign_reviewers(
    db: AsyncSession,
    cycle_id: str,
    subject_id: str,
    reviewer_ids: List[str],
    relationship_type: str = "peer",
    is_anonymous: bool = True,
) -> List[Review]:
    cycle = await db.get(ReviewCycle, cycle_id)
    if not cycle:
        raise ValueError(f"Review cycle {cycle_id} not found")

    reviews = []
    for reviewer_id in reviewer_ids:
        review = Review(
            id=uuid.uuid4().hex,
            cycle_id=cycle_id,
            subject_id=subject_id,
            reviewer_id=reviewer_id,
            relationship_type=relationship_type,
            is_anonymous=is_anonymous,
            status="pending",
        )
        db.add(review)
        reviews.append(review)

    await db.commit()
    logger.info(f"Assigned {len(reviews)} reviewers for subject {subject_id} in cycle {cycle_id[:8]}")
    return reviews


async def submit_review(
    db: AsyncSession,
    review_id: str,
    overall_rating: float,
    ratings: List[Dict[str, Any]],
    strengths: str = "",
    improvements: str = "",
    comments: str = "",
) -> Review:
    review = await db.get(Review, review_id)
    if not review:
        raise ValueError(f"Review {review_id} not found")
    if review.status not in ("pending", "draft"):
        raise ValueError(f"Review already submitted")

    review.overall_rating = overall_rating
    review.strengths = strengths
    review.improvements = improvements
    review.comments = comments
    review.status = "submitted"
    review.submitted_at = datetime.now(timezone.utc)

    existing_ratings = await db.execute(
        select(ReviewRating).where(ReviewRating.review_id == review_id)
    )
    for r in existing_ratings.scalars().all():
        await db.delete(r)

    for rating in ratings:
        rr = ReviewRating(
            id=uuid.uuid4().hex,
            review_id=review_id,
            category=rating["category"],
            score=rating["score"],
            comment=rating.get("comment", ""),
        )
        db.add(rr)

    await db.commit()
    await db.refresh(review)
    logger.info(f"Review {review_id[:8]} submitted for subject {review.subject_id}")
    return review


async def get_subject_feedback(
    db: AsyncSession,
    subject_id: str,
    cycle_id: Optional[str] = None,
) -> Dict[str, Any]:
    query = select(Review).where(Review.subject_id == subject_id)
    if cycle_id:
        query = query.where(Review.cycle_id == cycle_id)
    query = query.where(Review.status == "submitted")
    result = await db.execute(query)
    reviews = result.scalars().all()

    if not reviews:
        return {"subject_id": subject_id, "total_reviews": 0, "average_rating": 0, "category_averages": {}, "reviews": []}

    total_rating = 0.0
    category_scores: Dict[str, List[int]] = {}
    review_summaries = []

    for review in reviews:
        total_rating += review.overall_rating or 0
        ratings_res = await db.execute(
            select(ReviewRating).where(ReviewRating.review_id == review.id)
        )
        ratings = ratings_res.scalars().all()
        review_data = {
            "review_id": review.id,
            "overall_rating": review.overall_rating,
            "relationship": review.relationship_type,
            "strengths": review.strengths,
            "improvements": review.improvements,
            "comments": review.comments,
            "submitted_at": review.submitted_at.isoformat() if review.submitted_at else None,
            "ratings": [
                {"category": r.category, "score": r.score, "comment": r.comment}
                for r in ratings
            ],
        }
        review_summaries.append(review_data)
        for r in ratings:
            if r.category not in category_scores:
                category_scores[r.category] = []
            category_scores[r.category].append(r.score)

    avg_rating = round(total_rating / len(reviews), 2)
    category_avgs = {
        cat: round(sum(scores) / len(scores), 2)
        for cat, scores in category_scores.items()
    }

    return {
        "subject_id": subject_id,
        "total_reviews": len(reviews),
        "average_rating": avg_rating,
        "category_averages": category_avgs,
        "reviews": review_summaries,
    }


async def get_cycle_progress(db: AsyncSession, cycle_id: str) -> Dict[str, Any]:
    cycle = await db.get(ReviewCycle, cycle_id)
    if not cycle:
        raise ValueError(f"Cycle {cycle_id} not found")

    total_res = await db.execute(
        select(func.count(Review.id)).where(Review.cycle_id == cycle_id)
    )
    total = total_res.scalar() or 0

    submitted_res = await db.execute(
        select(func.count(Review.id)).where(
            and_(Review.cycle_id == cycle_id, Review.status == "submitted")
        )
    )
    submitted = submitted_res.scalar() or 0

    subjects_res = await db.execute(
        select(func.count(func.distinct(Review.subject_id))).where(Review.cycle_id == cycle_id)
    )
    unique_subjects = subjects_res.scalar() or 0

    return {
        "cycle_id": cycle_id,
        "cycle_name": cycle.name,
        "status": cycle.status,
        "total_reviews": total,
        "submitted_reviews": submitted,
        "completion_pct": round(submitted / max(total, 1) * 100, 1),
        "unique_subjects": unique_subjects,
    }


async def generate_ai_summary(
    db: AsyncSession,
    subject_id: str,
    cycle_id: Optional[str] = None,
) -> str:
    feedback = await get_subject_feedback(db, subject_id, cycle_id)
    if feedback["total_reviews"] == 0:
        return "No reviews available to summarize."

    from app.services.llm_router import get_llm_client

    review_texts = []
    for r in feedback["reviews"]:
        parts = []
        if r.get("strengths"):
            parts.append(f"Strengths: {r['strengths']}")
        if r.get("improvements"):
            parts.append(f"Areas for improvement: {r['improvements']}")
        if r.get("comments"):
            parts.append(f"Comments: {r['comments']}")
        review_texts.append(" | ".join(parts))

    all_reviews = "\n\n".join(
        f"Review {i+1} (Overall: {r['overall_rating']}/5): {text}"
        for i, (r, text) in enumerate(zip(feedback["reviews"], review_texts))
    )

    prompt = f"""Summarize the following 360-degree feedback into a concise performance summary (3-5 sentences).
Highlight key strengths, areas for improvement, and notable patterns.

Average rating: {feedback['average_rating']}/5 from {feedback['total_reviews']} reviewers.

Reviews:
{all_reviews}

Summary:"""

    try:
        client, _ = await get_llm_client("gpt-4o-mini", None, db)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        return response.choices[0].message.content or "Summary unavailable."
    except Exception as e:
        logger.warning(f"AI summary generation failed: {e}")
        return f"Key findings: Average rating {feedback['average_rating']}/5 from {feedback['total_reviews']} reviewers."
