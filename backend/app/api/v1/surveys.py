from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.api.dependencies import get_tenant_db, require_roles
from app.services.pulse_surveys import create_pulse_survey, record_pulse_response, analyze_survey_sentiment, get_pulse_trends
from app.models.survey import PulseSurvey

router = APIRouter(tags=["Pulse Surveys"])

class SurveyCreate(BaseModel):
    title: str
    description: Optional[str] = None
    questions: List[Dict[str, Any]]

class SurveyResponsePayload(BaseModel):
    user_id: str
    answers: Dict[str, Any]

@router.post("/", status_code=201)
async def create_survey(
    payload: SurveyCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "manager"]))
):
    survey = await create_pulse_survey(db, payload.title, payload.description, payload.questions)
    return {"message": "Survey created", "id": survey.id}

@router.get("/")
async def list_surveys(db: AsyncSession = Depends(get_tenant_db)):
    stmt = select(PulseSurvey).order_by(PulseSurvey.created_at.desc())
    res = await db.execute(stmt)
    surveys = res.scalars().all()
    return [{
        "id": s.id,
        "title": s.title,
        "status": s.status,
        "created_at": s.created_at
    } for s in surveys]

@router.post("/{survey_id}/responses", status_code=201)
async def submit_response(
    survey_id: str,
    payload: SurveyResponsePayload,
    db: AsyncSession = Depends(get_tenant_db)
):
    try:
        resp = await record_pulse_response(db, survey_id, payload.user_id, payload.answers)
        return {"message": "Response recorded", "id": resp.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{survey_id}/sentiment")
async def get_survey_sentiment(
    survey_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "manager"]))
):
    result = await analyze_survey_sentiment(db, survey_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/trends")
async def get_engagement_trends(
    weeks: int = 8,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "manager"]))
):
    return await get_pulse_trends(db, weeks)
