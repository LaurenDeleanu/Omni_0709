"""
interview_kits.py — Structured interview kits with scorecards and rubrics.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime, timezone

from app.api.dependencies import get_tenant_db, get_current_user, require_roles

router = APIRouter(prefix="/interview-kits", tags=["Interview Kits"])


class CriterionDef(BaseModel):
    id: str
    name: str
    description: str
    max_score: int = 5
    weight: float = 1.0


class KitCreate(BaseModel):
    name: str
    description: str = ""
    job_title: str = ""
    criteria: list[CriterionDef] = []


class CandidateScore(BaseModel):
    candidate_id: str
    scores: dict  # criterion_id -> score


INTERVIEW_KITS = {}  # In-memory store (migrate to DB model later)


DEFAULT_KITS = [
    {
        "id": "kit-engineer",
        "name": "Software Engineer",
        "description": "Standard software engineering interview kit",
        "job_title": "Software Engineer",
        "criteria": [
            {"id": "tech-skills", "name": "Technical Skills", "description": "Coding, system design, debugging", "max_score": 5, "weight": 1.5},
            {"id": "problem-solving", "name": "Problem Solving", "description": "Analytical thinking, approach to problems", "max_score": 5, "weight": 1.5},
            {"id": "communication", "name": "Communication", "description": "Clarity, conciseness, active listening", "max_score": 5, "weight": 1.0},
            {"id": "culture", "name": "Cultural Fit", "description": "Values alignment, teamwork, adaptability", "max_score": 5, "weight": 1.0},
        ],
    },
    {
        "id": "kit-sales",
        "name": "Sales Representative",
        "description": "Standard sales interview kit",
        "job_title": "Sales Representative",
        "criteria": [
            {"id": "sales-acumen", "name": "Sales Acumen", "description": "Pipeline management, closing techniques", "max_score": 5, "weight": 1.5},
            {"id": "communication", "name": "Communication", "description": "Presentation, negotiation, persuasion", "max_score": 5, "weight": 1.5},
            {"id": "resilience", "name": "Resilience & Drive", "description": "Handling rejection, motivation", "max_score": 5, "weight": 1.0},
            {"id": "product-knowledge", "name": "Product Knowledge", "description": "Understanding of product and market", "max_score": 5, "weight": 1.0},
        ],
    },
    {
        "id": "kit-product",
        "name": "Product Manager",
        "description": "Standard product management interview kit",
        "job_title": "Product Manager",
        "criteria": [
            {"id": "strategy", "name": "Strategic Thinking", "description": "Vision, roadmap, prioritization", "max_score": 5, "weight": 1.5},
            {"id": "execution", "name": "Execution", "description": "Shipping, metrics, iteration", "max_score": 5, "weight": 1.5},
            {"id": "user-empathy", "name": "User Empathy", "description": "User research, personas, feedback", "max_score": 5, "weight": 1.0},
            {"id": "stakeholder", "name": "Stakeholder Management", "description": "Cross-functional collaboration, influence", "max_score": 5, "weight": 1.0},
        ],
    },
]


@router.get("")
async def list_kits(db: AsyncSession = Depends(get_tenant_db)):
    """List all interview kits (defaults + custom)."""
    all_kits = list(DEFAULT_KITS) + list(INTERVIEW_KITS.values())
    return {"kits": all_kits}


@router.get("/defaults")
async def get_default_kits():
    """Get default interview kits."""
    return {"kits": DEFAULT_KITS}


@router.post("")
async def create_kit(
    body: KitCreate,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_roles(["hr_admin", "super_admin", "manager", "recruiter"])),
):
    """Create a custom interview kit."""
    kit_id = uuid.uuid4().hex
    kit = {
        "id": kit_id,
        "name": body.name,
        "description": body.description,
        "job_title": body.job_title,
        "criteria": [c.model_dump() for c in body.criteria],
        "created_by": current_user.get("email", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    INTERVIEW_KITS[kit_id] = kit
    return kit


@router.post("/{kit_id}/score")
async def score_candidate(
    kit_id: str,
    body: CandidateScore,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: dict = Depends(get_current_user),
):
    """Score a candidate using an interview kit's rubric."""
    kit = INTERVIEW_KITS.get(kit_id)
    if not kit:
        kit = next((k for k in DEFAULT_KITS if k["id"] == kit_id), None)
    if not kit:
        raise HTTPException(status_code=404, detail="Interview kit not found")

    total_weighted = 0
    total_weight = 0
    breakdown = []

    for criterion in kit["criteria"]:
        cid = criterion["id"]
        score = body.scores.get(cid, 0)
        weighted = score * criterion["weight"]
        total_weighted += weighted
        total_weight += criterion["weight"]
        breakdown.append({
            "criterion_id": cid,
            "name": criterion["name"],
            "score": min(score, criterion["max_score"]),
            "max_score": criterion["max_score"],
            "weight": criterion["weight"],
            "weighted_score": round(weighted, 1),
        })

    overall = round(total_weighted / total_weight * 100 / 5, 1) if total_weight > 0 else 0

    return {
        "kit_id": kit_id,
        "candidate_id": body.candidate_id,
        "overall_score": min(overall, 100),
        "criteria_breakdown": breakdown,
        "recommendation": "strong_hire" if overall >= 85 else "hire" if overall >= 70 else "maybe" if overall >= 50 else "pass",
    }
