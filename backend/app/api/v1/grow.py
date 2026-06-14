from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.api.dependencies import get_tenant_db, get_current_user
from app.models.grow import Objective, KeyResult, PerformanceReview, ReviewNomination, ReviewResponse
from app.schemas.grow import (
    ObjectiveCreate, ObjectiveUpdate, ObjectiveOut,
    KeyResultCreate, KeyResultUpdate, KeyResultOut,
    PerformanceReviewCreate, PerformanceReviewUpdate, PerformanceReviewOut,
    ReviewNominationCreate, ReviewNominationOut,
    ReviewResponseCreate, ReviewResponseUpdate, ReviewResponseOut,
    GoalGenerationRequest, GoalGenerationResponse,
    TeamObjectivesRequest, TeamObjectivesResponse,
    GoalAlignmentResponse, DevelopmentGoalsResponse,
    GoalAdjustmentRequest, GoalAdjustmentResponse,
)
from sqlalchemy.orm import selectinload

router = APIRouter(dependencies=[Depends(get_current_user)])

# --- OKRs ---

@router.get("/okrs", response_model=List[ObjectiveOut])
async def get_objectives(
    owner_id: str = None,
    db: AsyncSession = Depends(get_tenant_db)
):
    query = select(Objective).options(selectinload(Objective.key_results))
    if owner_id:
        query = query.where(Objective.owner_id == owner_id)
    
    result = await db.execute(query)
    objectives = result.scalars().all()
    return objectives

@router.post("/okrs", response_model=ObjectiveOut)
async def create_objective(
    obj_in: ObjectiveCreate,
    db: AsyncSession = Depends(get_tenant_db)
):
    new_obj = Objective(
        title=obj_in.title,
        description=obj_in.description,
        owner_id=obj_in.owner_id,
        status=obj_in.status
    )
    db.add(new_obj)
    await db.flush() # To get the new_obj.id

    for kr_in in obj_in.key_results:
        new_kr = KeyResult(
            objective_id=new_obj.id,
            title=kr_in.title,
            target_value=kr_in.target_value,
            current_value=kr_in.current_value,
            unit=kr_in.unit
        )
        db.add(new_kr)

    await db.commit()
    await db.refresh(new_obj)
    
    # Reload with relationships
    query = select(Objective).options(selectinload(Objective.key_results)).where(Objective.id == new_obj.id)
    result = await db.execute(query)
    return result.scalar_one()

@router.put("/okrs/{id}", response_model=ObjectiveOut)
async def update_objective(
    id: str,
    obj_in: ObjectiveUpdate,
    db: AsyncSession = Depends(get_tenant_db)
):
    query = select(Objective).options(selectinload(Objective.key_results)).where(Objective.id == id)
    result = await db.execute(query)
    obj = result.scalar_one_or_none()
    
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")
        
    update_data = obj_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(obj, key, value)
        
    await db.commit()
    await db.refresh(obj)
    return obj

@router.delete("/okrs/{id}")
async def delete_objective(
    id: str,
    db: AsyncSession = Depends(get_tenant_db)
):
    result = await db.execute(select(Objective).where(Objective.id == id))
    obj = result.scalar_one_or_none()
    
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")
        
    await db.delete(obj)
    await db.commit()
    return {"message": "Objective deleted successfully"}

@router.post("/okrs/{objective_id}/key-results", response_model=KeyResultOut)
async def add_key_result(
    objective_id: str,
    kr_in: KeyResultCreate,
    db: AsyncSession = Depends(get_tenant_db)
):
    result = await db.execute(select(Objective).where(Objective.id == objective_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Objective not found")

    new_kr = KeyResult(
        objective_id=objective_id,
        title=kr_in.title,
        target_value=kr_in.target_value,
        current_value=kr_in.current_value,
        unit=kr_in.unit
    )
    db.add(new_kr)
    await db.commit()
    await db.refresh(new_kr)
    return new_kr

@router.put("/key-results/{id}", response_model=KeyResultOut)
async def update_key_result(
    id: str,
    kr_in: KeyResultUpdate,
    db: AsyncSession = Depends(get_tenant_db)
):
    result = await db.execute(select(KeyResult).where(KeyResult.id == id))
    kr = result.scalar_one_or_none()
    if not kr:
        raise HTTPException(status_code=404, detail="KeyResult not found")

    update_data = kr_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(kr, key, value)

    await db.commit()
    await db.refresh(kr)
    return kr

@router.delete("/key-results/{id}")
async def delete_key_result(
    id: str,
    db: AsyncSession = Depends(get_tenant_db)
):
    result = await db.execute(select(KeyResult).where(KeyResult.id == id))
    kr = result.scalar_one_or_none()
    if not kr:
        raise HTTPException(status_code=404, detail="KeyResult not found")

    await db.delete(kr)
    await db.commit()
    return {"message": "KeyResult deleted successfully"}


# --- Performance Reviews ---

@router.get("/reviews", response_model=List[PerformanceReviewOut])
async def get_reviews(
    employee_id: str = None,
    manager_id: str = None,
    db: AsyncSession = Depends(get_tenant_db)
):
    query = select(PerformanceReview)
    if employee_id:
        query = query.where(PerformanceReview.employee_id == employee_id)
    if manager_id:
        query = query.where(PerformanceReview.manager_id == manager_id)
        
    result = await db.execute(query.options(selectinload(PerformanceReview.nominations), selectinload(PerformanceReview.responses)))
    return result.scalars().all()

@router.post("/reviews", response_model=PerformanceReviewOut)
async def create_review(
    review_in: PerformanceReviewCreate,
    db: AsyncSession = Depends(get_tenant_db)
):
    new_review = PerformanceReview(**review_in.dict())
    db.add(new_review)
    await db.commit()
    await db.refresh(new_review)
    
    query = select(PerformanceReview).options(selectinload(PerformanceReview.nominations), selectinload(PerformanceReview.responses)).where(PerformanceReview.id == new_review.id)
    result = await db.execute(query)
    return result.scalar_one()

@router.put("/reviews/{id}", response_model=PerformanceReviewOut)
async def update_review(
    id: str,
    review_in: PerformanceReviewUpdate,
    db: AsyncSession = Depends(get_tenant_db)
):
    result = await db.execute(select(PerformanceReview).where(PerformanceReview.id == id))
    review = result.scalar_one_or_none()
    
    if not review:
        raise HTTPException(status_code=404, detail="PerformanceReview not found")
        
    update_data = review_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(review, key, value)
        
    await db.commit()
    await db.refresh(review)
    
    query = select(PerformanceReview).options(selectinload(PerformanceReview.nominations), selectinload(PerformanceReview.responses)).where(PerformanceReview.id == review.id)
    result = await db.execute(query)
    return result.scalar_one()

@router.delete("/reviews/{id}")
async def delete_review(
    id: str,
    db: AsyncSession = Depends(get_tenant_db)
):
    result = await db.execute(select(PerformanceReview).where(PerformanceReview.id == id))
    review = result.scalar_one_or_none()
    
    if not review:
        raise HTTPException(status_code=404, detail="PerformanceReview not found")
        
    await db.delete(review)
    await db.commit()
    return {"message": "PerformanceReview deleted successfully"}

@router.post("/reviews/{id}/nominations", response_model=ReviewNominationOut)
async def create_review_nomination(
    id: str,
    nom_in: ReviewNominationCreate,
    db: AsyncSession = Depends(get_tenant_db)
):
    result = await db.execute(select(PerformanceReview).where(PerformanceReview.id == id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="PerformanceReview not found")
        
    new_nom = ReviewNomination(
        review_id=id,
        **nom_in.dict()
    )
    db.add(new_nom)
    await db.commit()
    await db.refresh(new_nom)
    return new_nom

@router.post("/reviews/{id}/responses", response_model=ReviewResponseOut)
async def create_review_response(
    id: str,
    resp_in: ReviewResponseCreate,
    db: AsyncSession = Depends(get_tenant_db)
):
    result = await db.execute(select(PerformanceReview).where(PerformanceReview.id == id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="PerformanceReview not found")
        
    new_resp = ReviewResponse(
        review_id=id,
        **resp_in.dict()
    )
    db.add(new_resp)
    await db.commit()
    await db.refresh(new_resp)
    return new_resp

@router.put("/responses/{id}", response_model=ReviewResponseOut)
async def update_review_response(
    id: str,
    resp_in: ReviewResponseUpdate,
    db: AsyncSession = Depends(get_tenant_db)
):
    result = await db.execute(select(ReviewResponse).where(ReviewResponse.id == id))
    resp = result.scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=404, detail="ReviewResponse not found")
        
    update_data = resp_in.dict(exclude_unset=True)
    from datetime import datetime, timezone
    
    for key, value in update_data.items():
        setattr(resp, key, value)
        
    if resp_in.status == "Submitted" and not resp.submitted_at:
        resp.submitted_at = datetime.now(timezone.utc)
        
    await db.commit()
    await db.refresh(resp)
    return resp


@router.post("/reviews/{id}/summarize")
async def summarize_review_endpoint(
    id: str,
    db: AsyncSession = Depends(get_tenant_db)
):
    result = await db.execute(select(PerformanceReview).where(PerformanceReview.id == id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="PerformanceReview not found")

    from app.services.review_summarizer import summarize_review
    summary = await summarize_review(id, db)
    return summary


@router.post("/reviews/cycle-summary")
async def cycle_summary_endpoint(
    cycle_name: str,
    db: AsyncSession = Depends(get_tenant_db)
):
    from app.services.review_summarizer import batch_summarize_cycle
    summary = await batch_summarize_cycle(cycle_name, db)
    return summary


@router.post("/goals/generate", response_model=GoalGenerationResponse)
async def generate_goals_endpoint(
    req: GoalGenerationRequest,
    db: AsyncSession = Depends(get_tenant_db)
):
    from app.services.goal_generator import generate_smart_goals
    result = await generate_smart_goals(req.employee_id, db, count=req.count)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/goals/team-generate", response_model=TeamObjectivesResponse)
async def generate_team_objectives_endpoint(
    req: TeamObjectivesRequest,
    db: AsyncSession = Depends(get_tenant_db)
):
    from app.services.goal_generator import generate_team_objectives
    result = await generate_team_objectives(req.team_id, req.quarter, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/goals/{employee_id}/alignment", response_model=GoalAlignmentResponse)
async def get_goal_alignment_endpoint(
    employee_id: str,
    db: AsyncSession = Depends(get_tenant_db)
):
    from app.services.goal_generator import align_goals_with_company_strategy
    result = await align_goals_with_company_strategy(employee_id, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/goals/{employee_id}/development", response_model=DevelopmentGoalsResponse)
async def get_development_goals_endpoint(
    employee_id: str,
    db: AsyncSession = Depends(get_tenant_db)
):
    from app.services.goal_generator import generate_career_development_goals
    result = await generate_career_development_goals(employee_id, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.patch("/goals/{employee_id}/adjust", response_model=GoalAdjustmentResponse)
async def suggest_adjustments_endpoint(
    employee_id: str,
    req: GoalAdjustmentRequest,
    db: AsyncSession = Depends(get_tenant_db)
):
    from app.services.goal_generator import suggest_goal_adjustments
    result = await suggest_goal_adjustments(employee_id, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/career-paths/{role_id}")
async def get_career_path_endpoint(
    role_id: str,
    db: AsyncSession = Depends(get_tenant_db)
):
    """
    Returns a tree of possible career tracks starting from the given role_id.
    """
    from app.services.career_path import generate_career_path
    result = await generate_career_path(db, role_id)
    return result
