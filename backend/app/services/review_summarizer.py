import json
import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.models.grow import PerformanceReview
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

SUMMARY_TTL = 3600


async def summarize_review(review_id: str, db: AsyncSession) -> dict:
    cache_key = f"review_summary:{review_id}"
    r = await get_redis()
    cached = await r.get(cache_key)
    if cached:
        return json.loads(cached)

    result = await db.execute(select(PerformanceReview).where(PerformanceReview.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        return {"error": f"Review {review_id} not found"}

    self_eval = review.self_evaluation or {}
    mgr_eval = review.manager_evaluation or {}
    feedback_list = review.self_evaluation.get("peer_feedback", []) if review.self_evaluation else []

    all_text = json.dumps({
        "self_evaluation": self_eval,
        "manager_evaluation": mgr_eval,
        "peer_feedback": feedback_list,
    }, ensure_ascii=False)

    try:
        from app.services.llm_router import get_llm_client
        client, _ = await get_llm_client("gpt-4o-mini", None, db)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an HR performance review summarizer. Analyze the performance review data and return a structured JSON object with these keys: "
                        "strengths (list of strings), areas_for_improvement (list of strings), overall_rating (integer 1-5), "
                        "key_quote (string - a representative quote from the review), action_items (list of strings). "
                        "Be concise and objective. If data is incomplete, note that in the output."
                    ),
                },
                {"role": "user", "content": all_text[:8000]},
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        raw = response.choices[0].message.content or "{}"
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {
                "strengths": ["Unable to parse"],
                "areas_for_improvement": ["Unable to parse"],
                "overall_rating": 3,
                "key_quote": "",
                "action_items": [],
            }
    except Exception as e:
        logger.error(f"LLM summarization failed for review {review_id}: {e}")
        parsed = {
            "strengths": [],
            "areas_for_improvement": [],
            "overall_rating": 3,
            "key_quote": "",
            "action_items": [],
            "error": f"Summarization failed: {str(e)}",
        }

    summary = {
        "review_id": review_id,
        "cycle_name": review.cycle_name,
        "employee_id": review.employee_id,
        "manager_id": review.manager_id,
        "status": review.status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **parsed,
    }

    await r.setex(cache_key, SUMMARY_TTL, json.dumps(summary, default=str))
    return summary


async def batch_summarize_cycle(cycle_name: str, db: AsyncSession) -> dict:
    result = await db.execute(select(PerformanceReview).where(PerformanceReview.cycle_name == cycle_name))
    reviews = result.scalars().all()

    if not reviews:
        return {"cycle_name": cycle_name, "error": "No reviews found for this cycle"}

    summaries = []
    ratings = []
    all_strengths: List[str] = []
    all_areas: List[str] = []
    all_actions: List[str] = []

    for review in reviews:
        summary = await summarize_review(review.id, db)
        summaries.append(summary)
        if summary.get("overall_rating"):
            try:
                ratings.append(int(summary["overall_rating"]))
            except (ValueError, TypeError):
                pass
        all_strengths.extend(summary.get("strengths", []))
        all_areas.extend(summary.get("areas_for_improvement", []))
        all_actions.extend(summary.get("action_items", []))

    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0

    top_strengths = list(dict.fromkeys(all_strengths))[:5] if all_strengths else []
    top_areas = list(dict.fromkeys(all_areas))[:5] if all_areas else []
    top_actions = list(dict.fromkeys(all_actions))[:5] if all_actions else []

    return {
        "cycle_name": cycle_name,
        "review_count": len(reviews),
        "average_rating": avg_rating,
        "rating_distribution": {
            "1": ratings.count(1), "2": ratings.count(2), "3": ratings.count(3),
            "4": ratings.count(4), "5": ratings.count(5),
        },
        "top_strengths": top_strengths,
        "top_areas_for_improvement": top_areas,
        "top_action_items": top_actions,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
