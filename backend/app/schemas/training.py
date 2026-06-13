from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


# ==========================================
# COURSE SCHEMAS
# ==========================================
class CourseBase(BaseModel):
    title: str
    description: Optional[str] = None
    is_scorm: bool = False
    scorm_version: Optional[str] = None
    package_url: Optional[str] = None
    min_duration_hours: float = 2.0
    is_fundae_eligible: bool = True


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_scorm: Optional[bool] = None
    scorm_version: Optional[str] = None
    package_url: Optional[str] = None
    min_duration_hours: Optional[float] = None
    is_fundae_eligible: Optional[bool] = None


class CourseResponse(CourseBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# COURSE ENROLLMENTS SCHEMAS
# ==========================================
class CourseEnrollmentBase(BaseModel):
    user_id: str
    course_id: str
    status: str = "enrolled"
    progress_percentage: float = 0.0
    scorm_suspend_data: Optional[str] = None
    score: Optional[float] = None
    time_spent_seconds: int = 0
    completed_at: Optional[datetime] = None


class CourseEnrollmentCreate(BaseModel):
    user_id: str
    course_id: str


class CourseEnrollmentUpdate(BaseModel):
    status: Optional[str] = None
    progress_percentage: Optional[float] = None
    scorm_suspend_data: Optional[str] = None
    score: Optional[float] = None
    time_spent_seconds: Optional[int] = None
    completed_at: Optional[datetime] = None


class CourseEnrollmentResponse(CourseEnrollmentBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# FUNDAE VALIDATION SCHEMAS
# ==========================================
class FundaeValidationBase(BaseModel):
    enrollment_id: str
    duration_valid: bool = False
    progress_valid: bool = False
    test_valid: bool = False
    survey_valid: bool = False
    overall_eligible: bool = False


class FundaeValidationResponse(FundaeValidationBase):
    id: str
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)
