from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class KeyResultBase(BaseModel):
    title: str
    target_value: int
    current_value: Optional[int] = 0
    unit: Optional[str] = "%"

class KeyResultCreate(KeyResultBase):
    pass

class KeyResultUpdate(BaseModel):
    title: Optional[str] = None
    target_value: Optional[int] = None
    current_value: Optional[int] = None
    unit: Optional[str] = None

class KeyResultOut(KeyResultBase):
    id: str
    objective_id: str

    class Config:
        from_attributes = True

class ObjectiveBase(BaseModel):
    title: str
    description: Optional[str] = None
    owner_id: str
    status: Optional[str] = "On Track"

class ObjectiveCreate(ObjectiveBase):
    key_results: Optional[List[KeyResultCreate]] = []

class ObjectiveUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    owner_id: Optional[str] = None
    status: Optional[str] = None

class ObjectiveOut(ObjectiveBase):
    id: str
    created_at: datetime
    key_results: List[KeyResultOut] = []

    class Config:
        from_attributes = True

class PerformanceReviewBase(BaseModel):
    employee_id: str
    manager_id: str
    cycle_name: str
    status: Optional[str] = "Draft"

class PerformanceReviewCreate(PerformanceReviewBase):
    pass

class PerformanceReviewUpdate(BaseModel):
    status: Optional[str] = None
    self_evaluation: Optional[Dict[str, Any]] = None
    manager_evaluation: Optional[Dict[str, Any]] = None

class ReviewNominationBase(BaseModel):
    nominator_id: str
    nominee_id: str
    relationship_type: str

class ReviewNominationCreate(ReviewNominationBase):
    pass

class ReviewNominationOut(ReviewNominationBase):
    id: str
    review_id: str
    status: str

    class Config:
        from_attributes = True

class ReviewResponseBase(BaseModel):
    reviewer_id: str
    relationship_type: str
    feedback: Optional[Dict[str, Any]] = None
    is_anonymous: Optional[bool] = True

class ReviewResponseCreate(ReviewResponseBase):
    pass

class ReviewResponseUpdate(BaseModel):
    feedback: Optional[Dict[str, Any]] = None
    status: Optional[str] = "Submitted"

class ReviewResponseOut(ReviewResponseBase):
    id: str
    review_id: str
    status: str
    created_at: datetime
    submitted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PerformanceReviewOut(PerformanceReviewBase):
    id: str
    self_evaluation: Optional[Dict[str, Any]] = None
    manager_evaluation: Optional[Dict[str, Any]] = None
    created_at: datetime
    nominations: List[ReviewNominationOut] = []
    responses: List[ReviewResponseOut] = []

    class Config:
        from_attributes = True


class GoalGenerationRequest(BaseModel):
    employee_id: str
    count: int = Field(default=3, ge=1, le=10)
    quarter: Optional[str] = None


class GoalGenerationResponse(BaseModel):
    goals: List[Dict[str, Any]] = []
    alignment_explanation: str = ""


class TeamObjectivesRequest(BaseModel):
    team_id: str
    quarter: str


class TeamObjectivesResponse(BaseModel):
    team_objectives: List[Dict[str, Any]] = []
    strategy_cascade: str = ""
    quarter: str = ""


class GoalAlignmentResponse(BaseModel):
    alignment_map: List[Dict[str, Any]] = []
    misaligned_goals: List[Dict[str, Any]] = []
    goal_tree: Dict[str, Any] = {}
    summary: str = ""


class DevelopmentGoalsResponse(BaseModel):
    development_goals: List[Dict[str, Any]] = []


class GoalAdjustmentRequest(BaseModel):
    employee_id: str
    current_quarter: Optional[str] = None


class GoalAdjustmentResponse(BaseModel):
    adjustments: List[Dict[str, Any]] = []
    summary: str = ""
