from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid

from app.api.dependencies import get_tenant_db, get_current_user, require_roles
from app.models.interview import (
    InterviewScorecard, ScorecardCriterion,
    InterviewKit, InterviewStage,
    CandidateEvaluation, CriterionScore,
)

router = APIRouter()


def _get_user_id(user_payload: dict) -> str:
    sub = user_payload.get("sub", "")
    if "|" in sub:
        return sub.split("|")[-1]
    return sub or "unknown"


# ── Schemas ──

class CriterionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    max_score: int = 5
    weight: float = 1.0
    sort_order: int = 0


class CriterionResponse(BaseModel):
    id: str
    scorecard_id: str
    name: str
    description: Optional[str] = None
    max_score: int
    weight: float
    sort_order: int
    model_config = {"from_attributes": True}


class ScorecardCreate(BaseModel):
    name: str
    role_title: str
    department: Optional[str] = None
    description: Optional[str] = None
    criteria: List[CriterionCreate] = []


class ScorecardResponse(BaseModel):
    id: str
    name: str
    role_title: str
    department: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    criteria_count: int = 0
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class ScorecardDetailResponse(ScorecardResponse):
    criteria: List[CriterionResponse] = []


class StageCreate(BaseModel):
    name: str
    description: Optional[str] = None
    duration_minutes: int = 30
    interviewer_role: str = "recruiter"
    sort_order: int = 0
    suggested_questions: list = []
    evaluation_focus: Optional[str] = None


class StageResponse(BaseModel):
    id: str
    kit_id: str
    name: str
    description: Optional[str] = None
    duration_minutes: int
    interviewer_role: str
    sort_order: int
    suggested_questions: list
    evaluation_focus: Optional[str] = None
    model_config = {"from_attributes": True}


class KitCreate(BaseModel):
    name: str
    role_title: str
    scorecard_id: Optional[str] = None
    description: Optional[str] = None
    total_duration_minutes: int = 60
    stages: List[StageCreate] = []


class KitResponse(BaseModel):
    id: str
    name: str
    role_title: str
    scorecard_id: Optional[str] = None
    description: Optional[str] = None
    total_duration_minutes: int
    is_active: bool
    stage_count: int = 0
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class KitDetailResponse(KitResponse):
    stages: List[StageResponse] = []


class CriterionScoreCreate(BaseModel):
    criterion_id: str
    criterion_name: str
    score: int
    notes: Optional[str] = None


class EvaluationCreate(BaseModel):
    candidate_id: str
    job_id: str
    scorecard_id: Optional[str] = None
    kit_id: Optional[str] = None
    stage_name: Optional[str] = None
    overall_notes: Optional[str] = None
    recommendation: str = "consider"
    scores: List[CriterionScoreCreate] = []


class CriterionScoreResponse(BaseModel):
    id: str
    evaluation_id: str
    criterion_id: str
    criterion_name: str
    score: int
    notes: Optional[str] = None
    model_config = {"from_attributes": True}


class EvaluationResponse(BaseModel):
    id: str
    candidate_id: str
    job_id: str
    scorecard_id: Optional[str] = None
    kit_id: Optional[str] = None
    interviewer_id: Optional[str] = None
    stage_name: Optional[str] = None
    overall_notes: Optional[str] = None
    recommendation: str
    created_at: datetime
    scores: List[CriterionScoreResponse] = []
    model_config = {"from_attributes": True}


# ── Scorecards ──

@router.get("/interview-scorecards", response_model=List[ScorecardResponse])
async def list_scorecards(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    result = await db.execute(select(InterviewScorecard).order_by(InterviewScorecard.created_at.desc()))
    scorecards = result.scalars().all()
    items = []
    for sc in scorecards:
        count_result = await db.scalar(select(func.count()).select_from(ScorecardCriterion).where(ScorecardCriterion.scorecard_id == sc.id))
        items.append(ScorecardResponse(
            id=sc.id, name=sc.name, role_title=sc.role_title,
            department=sc.department, description=sc.description,
            is_active=sc.is_active, criteria_count=count_result or 0,
            created_at=sc.created_at, updated_at=sc.updated_at,
        ))
    return items


@router.post("/interview-scorecards", response_model=ScorecardDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_scorecard(
    data: ScorecardCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    sc = InterviewScorecard(
        id=uuid.uuid4().hex, name=data.name, role_title=data.role_title,
        department=data.department, description=data.description,
        created_by=_get_user_id(current_user),
    )
    db.add(sc)
    await db.flush()

    criteria = []
    for i, c in enumerate(data.criteria):
        crit = ScorecardCriterion(
            id=uuid.uuid4().hex, scorecard_id=sc.id, name=c.name,
            description=c.description, max_score=c.max_score,
            weight=c.weight, sort_order=c.sort_order or i,
        )
        db.add(crit)
        criteria.append(CriterionResponse(
            id=crit.id, scorecard_id=sc.id, name=crit.name,
            description=crit.description, max_score=crit.max_score,
            weight=crit.weight, sort_order=crit.sort_order,
        ))

    await db.commit()
    return ScorecardDetailResponse(
        id=sc.id, name=sc.name, role_title=sc.role_title,
        department=sc.department, description=sc.description,
        is_active=sc.is_active, criteria_count=len(criteria),
        criteria=criteria, created_at=sc.created_at, updated_at=sc.updated_at,
    )


@router.get("/interview-scorecards/{scorecard_id}", response_model=ScorecardDetailResponse)
async def get_scorecard(
    scorecard_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    result = await db.execute(select(InterviewScorecard).where(InterviewScorecard.id == scorecard_id))
    sc = result.scalar_one_or_none()
    if not sc:
        raise HTTPException(status_code=404, detail="Scorecard not found")

    crit_result = await db.execute(select(ScorecardCriterion).where(ScorecardCriterion.scorecard_id == sc.id).order_by(ScorecardCriterion.sort_order))
    criteria = crit_result.scalars().all()

    return ScorecardDetailResponse(
        id=sc.id, name=sc.name, role_title=sc.role_title,
        department=sc.department, description=sc.description,
        is_active=sc.is_active, criteria_count=len(criteria),
        criteria=[CriterionResponse(
            id=c.id, scorecard_id=c.scorecard_id, name=c.name,
            description=c.description, max_score=c.max_score,
            weight=c.weight, sort_order=c.sort_order,
        ) for c in criteria],
        created_at=sc.created_at, updated_at=sc.updated_at,
    )


@router.delete("/interview-scorecards/{scorecard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scorecard(
    scorecard_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    result = await db.execute(select(InterviewScorecard).where(InterviewScorecard.id == scorecard_id))
    sc = result.scalar_one_or_none()
    if not sc:
        raise HTTPException(status_code=404, detail="Scorecard not found")
    await db.delete(sc)
    await db.commit()
    return None


# ── Interview Kits ──

@router.get("/interview-kits", response_model=List[KitResponse])
async def list_kits(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    result = await db.execute(select(InterviewKit).order_by(InterviewKit.created_at.desc()))
    kits = result.scalars().all()
    items = []
    for k in kits:
        stage_count = await db.scalar(select(func.count()).select_from(InterviewStage).where(InterviewStage.kit_id == k.id))
        items.append(KitResponse(
            id=k.id, name=k.name, role_title=k.role_title,
            scorecard_id=k.scorecard_id, description=k.description,
            total_duration_minutes=k.total_duration_minutes,
            is_active=k.is_active, stage_count=stage_count or 0,
            created_at=k.created_at, updated_at=k.updated_at,
        ))
    return items


@router.post("/interview-kits", response_model=KitDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_kit(
    data: KitCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    kit = InterviewKit(
        id=uuid.uuid4().hex, name=data.name, role_title=data.role_title,
        scorecard_id=data.scorecard_id, description=data.description,
        total_duration_minutes=data.total_duration_minutes,
        created_by=_get_user_id(current_user),
    )
    db.add(kit)
    await db.flush()

    stages = []
    for i, s in enumerate(data.stages):
        stage = InterviewStage(
            id=uuid.uuid4().hex, kit_id=kit.id, name=s.name,
            description=s.description, duration_minutes=s.duration_minutes,
            interviewer_role=s.interviewer_role, sort_order=s.sort_order or i,
            suggested_questions=s.suggested_questions,
            evaluation_focus=s.evaluation_focus,
        )
        db.add(stage)
        stages.append(StageResponse(
            id=stage.id, kit_id=kit.id, name=stage.name,
            description=stage.description, duration_minutes=stage.duration_minutes,
            interviewer_role=stage.interviewer_role, sort_order=stage.sort_order,
            suggested_questions=stage.suggested_questions,
            evaluation_focus=stage.evaluation_focus,
        ))

    await db.commit()
    return KitDetailResponse(
        id=kit.id, name=kit.name, role_title=kit.role_title,
        scorecard_id=kit.scorecard_id, description=kit.description,
        total_duration_minutes=kit.total_duration_minutes,
        is_active=kit.is_active, stage_count=len(stages),
        stages=stages, created_at=kit.created_at, updated_at=kit.updated_at,
    )


# ── Candidate Evaluations ──

@router.post("/candidate-evaluations", response_model=EvaluationResponse, status_code=status.HTTP_201_CREATED)
async def submit_evaluation(
    data: EvaluationCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "recruiter", "manager"]))
):
    user_id = _get_user_id(current_user)

    eval = CandidateEvaluation(
        id=uuid.uuid4().hex, candidate_id=data.candidate_id, job_id=data.job_id,
        scorecard_id=data.scorecard_id, kit_id=data.kit_id,
        interviewer_id=user_id, stage_name=data.stage_name,
        overall_notes=data.overall_notes, recommendation=data.recommendation,
    )
    db.add(eval)
    await db.flush()

    scores = []
    for s in data.scores:
        cs = CriterionScore(
            id=uuid.uuid4().hex, evaluation_id=eval.id, criterion_id=s.criterion_id,
            criterion_name=s.criterion_name, score=s.score, notes=s.notes,
        )
        db.add(cs)
        scores.append(CriterionScoreResponse(
            id=cs.id, evaluation_id=eval.id, criterion_id=cs.criterion_id,
            criterion_name=cs.criterion_name, score=cs.score, notes=cs.notes,
        ))

    await db.commit()
    return EvaluationResponse(
        id=eval.id, candidate_id=eval.candidate_id, job_id=eval.job_id,
        scorecard_id=eval.scorecard_id, kit_id=eval.kit_id,
        interviewer_id=eval.interviewer_id, stage_name=eval.stage_name,
        overall_notes=eval.overall_notes, recommendation=eval.recommendation,
        created_at=eval.created_at, scores=scores,
    )


@router.get("/candidate-evaluations/{candidate_id}", response_model=List[EvaluationResponse])
async def get_candidate_evaluations(
    candidate_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    result = await db.execute(
        select(CandidateEvaluation).where(CandidateEvaluation.candidate_id == candidate_id).order_by(CandidateEvaluation.created_at.desc())
    )
    evals = result.scalars().all()

    items = []
    for ev in evals:
        scores_result = await db.execute(select(CriterionScore).where(CriterionScore.evaluation_id == ev.id))
        scores = scores_result.scalars().all()
        items.append(EvaluationResponse(
            id=ev.id, candidate_id=ev.candidate_id, job_id=ev.job_id,
            scorecard_id=ev.scorecard_id, kit_id=ev.kit_id,
            interviewer_id=ev.interviewer_id, stage_name=ev.stage_name,
            overall_notes=ev.overall_notes, recommendation=ev.recommendation,
            created_at=ev.created_at,
            scores=[CriterionScoreResponse(
                id=s.id, evaluation_id=s.evaluation_id, criterion_id=s.criterion_id,
                criterion_name=s.criterion_name, score=s.score, notes=s.notes,
            ) for s in scores],
        ))
    return items
