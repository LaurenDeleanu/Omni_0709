import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.survey import PulseSurvey, PulseResponse
from app.models.user import User
from app.services.llm_router import get_llm_client
import json

logger = logging.getLogger("successcore.pulse")


async def create_pulse_survey(db: AsyncSession, title: str, description: Optional[str], questions: List[Dict[str, Any]]) -> PulseSurvey:
    survey = PulseSurvey(
        title=title,
        description=description,
        status="active",
        questions=questions
    )
    db.add(survey)
    await db.commit()
    await db.refresh(survey)
    return survey


async def record_pulse_response(db: AsyncSession, survey_id: str, user_id: str, answers: Dict[str, Any]) -> PulseResponse:
    # Check if user already responded
    stmt = select(PulseResponse).where(PulseResponse.survey_id == survey_id, PulseResponse.user_id == user_id)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise ValueError("User has already responded to this survey")

    response = PulseResponse(
        survey_id=survey_id,
        user_id=user_id,
        answers=answers
    )
    db.add(response)
    await db.commit()
    await db.refresh(response)
    return response


async def analyze_survey_sentiment(db: AsyncSession, survey_id: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    stmt = select(PulseResponse).where(PulseResponse.survey_id == survey_id)
    res = await db.execute(stmt)
    responses = res.scalars().all()

    if not responses:
        return {"error": "No responses found for this survey"}

    # Aggregate text responses
    text_responses = []
    for r in responses:
        for k, v in r.answers.items():
            if isinstance(v, str) and len(v) > 5:
                text_responses.append(v)

    if not text_responses:
        return {"sentiment": "neutral", "summary": "No text responses to analyze", "topics": []}

    system_prompt = (
        "You are an HR sentiment analysis bot. Analyze the following survey text responses.\n"
        "Return a JSON object with: 'sentiment' (positive/neutral/negative), 'summary' (a brief overview), and 'topics' (list of main themes)."
    )
    user_prompt = "Responses:\n" + "\n- ".join(text_responses)

    client, _ = await get_llm_client(model)
    try:
        completion = await client.chat.completions.create(
            model=model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        logger.error(f"Failed to analyze sentiment: {e}")
        return {"error": str(e)}


async def get_pulse_trends(db: AsyncSession, weeks: int = 8) -> dict:
    users_res = await db.execute(select(User).where(User.is_active == True))
    users = users_res.scalars().all()
    user_dept_map = {u.id: (u.department or "Unknown") for u in users}

    # Fetch responses from the last N weeks
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    stmt = select(PulseResponse).where(PulseResponse.submitted_at >= cutoff)
    res = await db.execute(stmt)
    responses = res.scalars().all()

    trends: Dict[str, dict] = {}
    for d in set(user_dept_map.values()):
        trends[d] = {"total_responses": 0, "score_sum": 0, "breakdown": {}}

    for r in responses:
        dept = user_dept_map.get(r.user_id, "Unknown")
        if dept not in trends:
            trends[dept] = {"total_responses": 0, "score_sum": 0, "breakdown": {}}

        # Assume answers might contain a 'rating' key or values that are integers
        for k, v in r.answers.items():
            if isinstance(v, int):
                trends[dept]["total_responses"] += 1
                trends[dept]["score_sum"] += v
                trends[dept]["breakdown"][k] = trends[dept]["breakdown"].get(k, 0) + v

    response_count = sum(t["total_responses"] for t in trends.values())
    if response_count == 0:
        return {"overall_avg": 0, "total_responses": 0, "departments": [], "trend": "no_data", "recommended_actions": []}

    overall_sum = sum(t["score_sum"] for t in trends.values())
    overall_avg = round(overall_sum / response_count, 2)

    departments = []
    for dept, data in trends.items():
        if data["total_responses"] == 0:
            continue
        avg = round(data["score_sum"] / data["total_responses"], 2)
        departments.append({
            "department": dept,
            "avg_score": avg,
            "response_count": data["total_responses"],
            "sentiment": "positive" if avg > 3.5 else "neutral" if avg > 2.5 else "negative",
        })

    return {
        "overall_avg": overall_avg,
        "total_responses": response_count,
        "departments": departments,
        "trend": "improving" if overall_avg > 3.5 else "stable" if overall_avg > 2.5 else "declining",
        "recommended_actions": _generate_recommendations(departments),
    }


def _generate_recommendations(departments: list) -> List[str]:
    recs = []
    for d in departments:
        if d["sentiment"] == "negative":
            recs.append(f"Schedule a check-in with {d['department']} — avg score {d['avg_score']}")
        elif d["sentiment"] == "neutral":
            recs.append(f"Consider a team sync for {d['department']} (score {d['avg_score']})")
    return recs
