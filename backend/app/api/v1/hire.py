from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import List, Optional
import uuid
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.dependencies import get_tenant_db, require_roles, check_module_enabled
from app.models.hire import JobPosting, Candidate, Interview, CandidatePool, CandidatePoolEntry
from app.models.user import User
from app.models.notification import Notification
from app.core.auth import hash_password
from pydantic import BaseModel, EmailStr
from datetime import datetime

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(dependencies=[Depends(check_module_enabled("hire"))])
public_router = APIRouter()

# ---------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------
class JobCreate(BaseModel):
    title: str
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    description: Optional[str] = None

class JobUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class CandidateCreate(BaseModel):
    job_id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    resume_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    source: Optional[str] = None

class CandidateUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    resume_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    notes: Optional[str] = None
    stage: Optional[str] = None

class InterviewCreate(BaseModel):
    interviewer_id: str
    scheduled_at: datetime
    duration_minutes: Optional[int] = 60
    interview_type: str
    feedback_notes: Optional[str] = None
    score: Optional[float] = None

class CandidatePromote(BaseModel):
    role: str = "employee"
    password: str
    phone_number: Optional[str] = None
    address: Optional[str] = None
    contract_type: Optional[str] = "Indefinido"
    hire_date: Optional[datetime] = None
    base_salary: Optional[float] = 50000.0
    social_security_number: Optional[str] = None
    iban: Optional[str] = None
    country: Optional[str] = "ES"
    assign_onboarding_plan: bool = False
    enroll_in_training: bool = False
    request_it_equipment: bool = False
    it_equipment_type: Optional[str] = None
    it_equipment_quantity: int = 1

class StageUpdate(BaseModel):
    stage: str

class PoolCreate(BaseModel):
    name: str
    description: Optional[str] = None

class PoolUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class AddToPoolRequest(BaseModel):
    candidate_id: str

class AddByStageRequest(BaseModel):
    stage: str

class CrmUpdateRequest(BaseModel):
    tags: Optional[str] = None
    last_contacted_at: Optional[datetime] = None
    engagement_score: Optional[float] = None
    source_detail: Optional[str] = None


# ---------------------------------------------------------
# Talent CRM — Candidate Pools
# ---------------------------------------------------------
@router.get("/pools")
async def list_pools(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter", "manager"]))
):
    stmt = select(CandidatePool).order_by(CandidatePool.created_at.desc())
    result = await db.execute(stmt)
    pools = result.scalars().all()
    
    response = []
    for pool in pools:
        count_stmt = select(func.count(CandidatePoolEntry.id)).where(CandidatePoolEntry.pool_id == pool.id)
        count_result = await db.execute(count_stmt)
        candidate_count = count_result.scalar() or 0
        response.append({
            "id": pool.id,
            "name": pool.name,
            "description": pool.description,
            "created_by_id": pool.created_by_id,
            "created_at": pool.created_at.isoformat() if pool.created_at else None,
            "candidate_count": candidate_count,
        })
    return response

@router.post("/pools", status_code=status.HTTP_201_CREATED)
async def create_pool(
    pool_in: PoolCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    pool = CandidatePool(
        id=uuid.uuid4().hex,
        name=pool_in.name,
        description=pool_in.description,
        created_by_id="system",
    )
    db.add(pool)
    await db.commit()
    return {"message": "Pool created successfully", "id": pool.id}

@router.put("/pools/{pool_id}")
async def update_pool(
    pool_id: str,
    pool_in: PoolUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    result = await db.execute(select(CandidatePool).where(CandidatePool.id == pool_id))
    pool = result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    update_data = pool_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pool, field, value)
    await db.commit()
    return {"message": "Pool updated successfully"}

@router.delete("/pools/{pool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pool(
    pool_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    result = await db.execute(select(CandidatePool).where(CandidatePool.id == pool_id))
    pool = result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    await db.delete(pool)
    await db.commit()
    return None

@router.get("/pools/{pool_id}/candidates")
async def get_pool_candidates(
    pool_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter", "manager"]))
):
    pool_result = await db.execute(select(CandidatePool).where(CandidatePool.id == pool_id))
    pool = pool_result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    
    stmt = (
        select(CandidatePoolEntry, Candidate)
        .join(Candidate, CandidatePoolEntry.candidate_id == Candidate.id)
        .where(CandidatePoolEntry.pool_id == pool_id)
        .order_by(CandidatePoolEntry.added_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    candidates = []
    for entry, candidate in rows:
        candidates.append({
            "entry_id": entry.id,
            "pool_id": entry.pool_id,
            "candidate_id": candidate.id,
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "email": candidate.email,
            "phone": candidate.phone,
            "stage": candidate.stage,
            "source": candidate.source,
            "engagement_score": candidate.engagement_score,
            "last_contacted_at": candidate.last_contacted_at.isoformat() if candidate.last_contacted_at else None,
            "source_detail": candidate.source_detail,
            "notes": entry.notes,
            "added_at": entry.added_at.isoformat() if entry.added_at else None,
        })
    return candidates

@router.post("/pools/{pool_id}/candidates", status_code=status.HTTP_201_CREATED)
async def add_to_pool(
    pool_id: str,
    payload: AddToPoolRequest,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    pool_result = await db.execute(select(CandidatePool).where(CandidatePool.id == pool_id))
    if not pool_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Pool not found")
    
    cand_result = await db.execute(select(Candidate).where(Candidate.id == payload.candidate_id))
    if not cand_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    existing = await db.execute(
        select(CandidatePoolEntry).where(
            CandidatePoolEntry.pool_id == pool_id,
            CandidatePoolEntry.candidate_id == payload.candidate_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Candidate already in pool")
    
    entry = CandidatePoolEntry(
        id=uuid.uuid4().hex,
        pool_id=pool_id,
        candidate_id=payload.candidate_id,
    )
    db.add(entry)
    await db.commit()
    return {"message": "Candidate added to pool", "id": entry.id}

@router.delete("/pools/{pool_id}/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_pool(
    pool_id: str,
    candidate_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    result = await db.execute(
        select(CandidatePoolEntry).where(
            CandidatePoolEntry.pool_id == pool_id,
            CandidatePoolEntry.candidate_id == candidate_id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Candidate not in pool")
    await db.delete(entry)
    await db.commit()
    return None

@router.post("/pools/{pool_id}/add-by-stage")
async def add_by_stage_to_pool(
    pool_id: str,
    payload: AddByStageRequest,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    pool_result = await db.execute(select(CandidatePool).where(CandidatePool.id == pool_id))
    if not pool_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Pool not found")
    
    cand_stmt = select(Candidate).where(Candidate.stage == payload.stage)
    cand_result = await db.execute(cand_stmt)
    candidates = cand_result.scalars().all()
    
    added = 0
    for candidate in candidates:
        existing = await db.execute(
            select(CandidatePoolEntry).where(
                CandidatePoolEntry.pool_id == pool_id,
                CandidatePoolEntry.candidate_id == candidate.id,
            )
        )
        if existing.scalar_one_or_none():
            continue
        entry = CandidatePoolEntry(
            id=uuid.uuid4().hex,
            pool_id=pool_id,
            candidate_id=candidate.id,
        )
        db.add(entry)
        added += 1
    
    await db.commit()
    return {"message": f"Added {added} candidates from stage '{payload.stage}' to pool", "added_count": added}

# ---------------------------------------------------------
# Talent CRM — Candidate CRM
# ---------------------------------------------------------
@router.get("/candidates/crm")
async def get_crm_candidates(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter", "manager"]))
):
    candidates_stmt = select(Candidate).order_by(Candidate.created_at.desc())
    candidates_result = await db.execute(candidates_stmt)
    candidates = candidates_result.scalars().all()
    
    response = []
    for c in candidates:
        pool_entries_stmt = (
            select(CandidatePool.id, CandidatePool.name)
            .join(CandidatePoolEntry, CandidatePoolEntry.pool_id == CandidatePool.id)
            .where(CandidatePoolEntry.candidate_id == c.id)
        )
        pool_result = await db.execute(pool_entries_stmt)
        pools = [{"id": row.id, "name": row.name} for row in pool_result.all()]
        
        response.append({
            "id": c.id,
            "job_id": c.job_id,
            "first_name": c.first_name,
            "last_name": c.last_name,
            "email": c.email,
            "phone": c.phone,
            "stage": c.stage,
            "source": c.source,
            "engagement_score": c.engagement_score,
            "last_contacted_at": c.last_contacted_at.isoformat() if c.last_contacted_at else None,
            "source_detail": c.source_detail,
            "pools": pools,
        })
    return response

@router.put("/candidates/{candidate_id}/crm")
async def update_crm_data(
    candidate_id: str,
    payload: CrmUpdateRequest,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(candidate, field, value)
    
    await db.commit()
    return {"message": "CRM data updated successfully"}

@router.post("/candidates/{candidate_id}/generate-outreach")
async def generate_outreach(
    candidate_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    job_title = ""
    if candidate.job_id:
        job_result = await db.execute(select(JobPosting).where(JobPosting.id == candidate.job_id))
        job = job_result.scalar_one_or_none()
        if job:
            job_title = job.title
    
    try:
        from openai import AsyncOpenAI
        import os
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            client = AsyncOpenAI(api_key=api_key)
            prompt = f"""Write a personalized nurture email for the following candidate:
Name: {candidate.first_name} {candidate.last_name}
Role applied for: {job_title or 'General position'}
Current pipeline stage: {candidate.stage}
Source: {candidate.source or 'Unknown'}

Write a warm, professional outreach email. Keep it under 200 words. Make it personal and engaging.
If the stage is 'interview', mention excitement about the upcoming conversation.
If the stage is 'offer', mention enthusiasm about possibly having them join the team.
If the stage is 'applied' or 'screening', express interest in learning more about them.
Return the response as plain JSON with keys: 'subject' and 'body'."""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
            data = __import__("json").loads(raw)
            return {"candidate_id": candidate_id, "subject": data.get("subject", ""), "body": data.get("body", ""), "ai_generated": True}
    except Exception:
        pass
    
    stage_messages = {
        "applied": "We received your application and would love to learn more about your experience.",
        "screening": "We're impressed by your profile and would like to schedule a conversation.",
        "interview": "We're looking forward to your upcoming interview and getting to know you better.",
        "offer": "We're excited about the possibility of you joining our team!",
        "hired": "Welcome aboard! We're thrilled to have you on the team.",
        "rejected": "Thank you for your interest. While we moved forward with other candidates, we'd love to stay in touch.",
    }
    body = stage_messages.get(candidate.stage, "Thank you for your interest in our team.")
    
    return {
        "candidate_id": candidate_id,
        "subject": f"Update from our team — {candidate.first_name}",
        "body": f"Hi {candidate.first_name},\n\n{body}\n\nBest regards,\nThe Hiring Team",
        "ai_generated": False,
    }

@router.post("/candidates/{candidate_id}/log-contact")
async def log_contact(
    candidate_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    candidate.last_contacted_at = datetime.now()
    await db.commit()
    return {"message": "Contact logged successfully", "last_contacted_at": candidate.last_contacted_at.isoformat()}

class CandidateRankRequest(BaseModel):
    candidate_ids: list[str]
    job_id: str

class PublicApplicationRequest(BaseModel):
    job_id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    resume_url: Optional[str] = None
    cover_letter: Optional[str] = None

class OfferLetterRequest(BaseModel):
    job_id: str
    salary: float
    start_date: str
    template: str

# ---------------------------------------------------------
# Rate limiting for AI screening endpoints
# ---------------------------------------------------------
import time
import asyncio
from collections import defaultdict

_screen_bucket: dict[str, tuple] = {}  # tenant_id -> (tokens, last_refill)
_screen_rate = 5.0 / 60.0  # 5 per minute
_screen_burst = 5
_rank_bucket: dict[str, tuple] = {}
_rank_rate = 3.0 / 60.0
_rank_burst = 3
_questions_bucket: dict[str, tuple] = {}
_questions_rate = 10.0 / 60.0
_questions_burst = 10

def _check_rate_limit(tenant_id: str, bucket_dict: dict, rate: float, burst: int) -> None:
    now = time.monotonic()
    tokens, last_refill = bucket_dict.get(tenant_id, (float(burst), now))
    elapsed = now - last_refill
    tokens = min(float(burst), tokens + elapsed * rate)
    if tokens < 1.0:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please retry shortly.", headers={"Retry-After": "15"})
    bucket_dict[tenant_id] = (tokens - 1.0, now)

def _get_tenant_id(request) -> str:
    if request is None:
        return "unknown"
    return request.headers.get("X-Tenant-ID", request.client.host if request.client else "unknown")

# ---------------------------------------------------------
# Job Endpoints
# ---------------------------------------------------------
@router.get("/jobs")
async def list_jobs(
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter", "manager"]))
):
    """Retrieve all open job postings with candidate counts."""
    count_stmt = select(
        Candidate.job_id, 
        func.count(Candidate.id).label("candidate_count")
    ).group_by(Candidate.job_id)
    counts = await db.execute(count_stmt)
    count_dict = {row.job_id: row.candidate_count for row in counts.all()}

    stmt = select(JobPosting).order_by(JobPosting.created_at.desc())
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    
    response = []
    for job in jobs:
        response.append({
            "id": job.id,
            "title": job.title,
            "department": job.department,
            "location": job.location,
            "employment_type": job.employment_type,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "candidate_count": count_dict.get(job.id, 0)
        })
    return response

@router.post("/jobs", status_code=status.HTTP_201_CREATED)
async def create_job(
    job_in: JobCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    """Create a new job posting."""
    job = JobPosting(
        id=uuid.uuid4().hex,
        title=job_in.title,
        department=job_in.department,
        location=job_in.location,
        employment_type=job_in.employment_type,
        description=job_in.description,
        status="open"
    )
    db.add(job)
    await db.commit()
    return {"message": "Job posting created successfully", "id": job.id}

@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter", "manager"]))
):
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "id": job.id,
        "title": job.title,
        "department": job.department,
        "location": job.location,
        "employment_type": job.employment_type,
        "description": job.description,
        "status": job.status
    }

@router.put("/jobs/{job_id}")
async def update_job(
    job_id: str,
    job_in: JobUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    """Update a job posting (e.g. title, description, or status to closed/draft)."""
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")

    update_data = job_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    await db.commit()
    await db.refresh(job)
    return {"message": "Job posting updated successfully"}

# ---------------------------------------------------------
# Candidate Endpoints
# ---------------------------------------------------------
@router.get("/candidates")
async def list_candidates(
    job_id: Optional[str] = None,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter", "manager"]))
):
    """List candidates, optionally filtered by job_id."""
    stmt = select(Candidate).order_by(Candidate.created_at.desc())
    if job_id:
        stmt = stmt.where(Candidate.job_id == job_id)
        
    result = await db.execute(stmt)
    candidates = result.scalars().all()
    
    return [{
        "id": c.id,
        "job_id": c.job_id,
        "first_name": c.first_name,
        "last_name": c.last_name,
        "email": c.email,
        "phone": c.phone,
        "resume_url": c.resume_url,
        "linkedin_url": c.linkedin_url,
        "portfolio_url": c.portfolio_url,
        "stage": c.stage,
        "source": c.source,
        "notes": c.notes,
        "engagement_score": c.engagement_score,
        "last_contacted_at": c.last_contacted_at.isoformat() if c.last_contacted_at else None,
        "source_detail": c.source_detail,
        "created_at": c.created_at.isoformat() if c.created_at else None
    } for c in candidates]

@router.post("/candidates", status_code=status.HTTP_201_CREATED)
async def add_candidate(
    candidate_in: CandidateCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    """Add a new candidate to a job pipeline."""
    job_res = await db.execute(select(JobPosting).where(JobPosting.id == candidate_in.job_id))
    if not job_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Job posting not found")

    candidate = Candidate(
        id=uuid.uuid4().hex,
        job_id=candidate_in.job_id,
        first_name=candidate_in.first_name,
        last_name=candidate_in.last_name,
        email=candidate_in.email,
        phone=candidate_in.phone,
        resume_url=candidate_in.resume_url,
        linkedin_url=candidate_in.linkedin_url,
        portfolio_url=candidate_in.portfolio_url,
        source=candidate_in.source,
        stage="applied",
        notes=""
    )
    db.add(candidate)
    await db.commit()
    return {"message": "Candidate added successfully", "id": candidate.id}

@router.put("/candidates/{candidate_id}")
async def update_candidate(
    candidate_id: str,
    candidate_in: CandidateUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    """Update candidate profile notes, contact information or links."""
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    update_data = candidate_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(candidate, field, value)

    await db.commit()
    await db.refresh(candidate)
    return {"message": "Candidate updated successfully"}

@router.patch("/candidates/{candidate_id}/stage")
async def update_candidate_stage(
    candidate_id: str,
    stage_in: StageUpdate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter", "manager"]))
):
    """Move candidate across Kanban stages."""
    valid_stages = ["applied", "screening", "interview", "offer", "hired", "rejected"]
    if stage_in.stage not in valid_stages:
        raise HTTPException(status_code=400, detail="Invalid stage")
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    old_stage = candidate.stage
    candidate.stage = stage_in.stage
    await db.commit()

    try:
        from app.services.event_sourcing import publish_event
        publish_event("candidate.stage_changed", {
            "candidate_id": candidate.id, "candidate_name": candidate.name,
            "job_id": candidate.job_id, "old_stage": old_stage, "new_stage": stage_in.stage
        }, tenant_id="acme_corp")
    except Exception:
        pass

    return {"message": f"Candidate moved to {stage_in.stage}"}


@router.post("/candidates/parse-resume")
async def parse_resume_endpoint(
    file: UploadFile = File(...),
    job_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter", "manager"]))
):
    """Upload a resume file (PDF, DOCX, TXT) and get AI-parsed structured candidate data."""
    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
    MAX_SIZE = 10 * 1024 * 1024

    filename = file.filename or "resume"
    ext = os.path.splitext(filename)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: '{ext}'. Accepted: .pdf, .docx, .txt")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum 10 MB.")

    from app.services.resume_parser import screen_resume, match_candidate_to_job
    try:
        result = await screen_resume(content, filename, job_id=job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume parsing failed: {str(e)}")

    if not result.get("success"):
        return result

    if job_id:
        job_res = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
        job = job_res.scalar_one_or_none()
        if job:
            requirements = f"Title: {job.title}\n"
            if job.department:
                requirements += f"Department: {job.department}\n"
            if job.description:
                requirements += f"Description: {job.description}\n"
            try:
                match_result = await match_candidate_to_job(result["candidate"], requirements)
                if match_result.get("success"):
                    result["job_match"] = match_result["match"]
                    result["job_id"] = job_id
                    result["job_title"] = job.title
            except Exception as e:
                result["job_match_error"] = str(e)

    return result

# ---------------------------------------------------------
# Interview Endpoints
# ---------------------------------------------------------
@router.get("/candidates/{candidate_id}/interviews")
async def list_interviews(
    candidate_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter", "manager"]))
):
    """Retrieve scheduled interviews with full interviewer name."""
    stmt = (
        select(Interview, User.full_name.label("interviewer_name"), User.email.label("interviewer_email"))
        .outerjoin(User, Interview.interviewer_id == User.id)
        .where(Interview.candidate_id == candidate_id)
        .order_by(Interview.scheduled_at.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    interviews = []
    for row in rows:
        interview = row[0]
        interviews.append({
            "id": interview.id,
            "candidate_id": interview.candidate_id,
            "interviewer_id": interview.interviewer_id,
            "interviewer_name": row.interviewer_name or "Evaluador Desconocido",
            "interviewer_email": row.interviewer_email,
            "scheduled_at": interview.scheduled_at.isoformat() if interview.scheduled_at else None,
            "duration_minutes": interview.duration_minutes,
            "interview_type": interview.interview_type,
            "feedback_notes": interview.feedback_notes,
            "score": interview.score
        })
    return interviews

@router.post("/candidates/{candidate_id}/interviews", status_code=status.HTTP_201_CREATED)
async def create_interview(
    candidate_id: str,
    interview_in: InterviewCreate,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    """Schedule an interview and record notes/score for candidate."""
    # Verify candidate exists
    cand_res = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = cand_res.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    interview = Interview(
        id=uuid.uuid4().hex,
        candidate_id=candidate_id,
        interviewer_id=interview_in.interviewer_id,
        scheduled_at=interview_in.scheduled_at,
        duration_minutes=interview_in.duration_minutes,
        interview_type=interview_in.interview_type,
        feedback_notes=interview_in.feedback_notes,
        score=interview_in.score
    )
    db.add(interview)
    await db.commit()

    try:
        from app.services.notification_utils import create_and_push_notification
        cand_name = f"{candidate.first_name} {candidate.last_name}"
        await create_and_push_notification(
            db,
            user_id=interview_in.interviewer_id,
            title="Interview Scheduled",
            message=f"You have an interview scheduled with {cand_name} at {interview_in.scheduled_at}",
            type_="task",
            link="/dashboard/hire?tab=interviews",
        )
        await db.commit()
    except Exception:
        pass

    return {"message": "Interview scheduled successfully", "id": interview.id}

@router.delete("/candidates/{candidate_id}/interviews/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview(
    candidate_id: str,
    interview_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    """Delete or cancel a scheduled interview."""
    result = await db.execute(select(Interview).where(Interview.id == interview_id, Interview.candidate_id == candidate_id))
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
        
    await db.delete(interview)
    await db.commit()
    return None

# ---------------------------------------------------------
# Candidate Promotion Endpoint (Onboarding Integration)
# ---------------------------------------------------------
@router.post("/candidates/{candidate_id}/promote")
async def promote_candidate(
    candidate_id: str,
    payload: CandidatePromote,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin"]))
):
    """
    Promote a candidate to an active Employee, pre-filling contact/personal details
    and setting up Spanish contract compliance. Schedules a welcomed app notification.
    """
    # Fetch candidate
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    # Verify email is not already taken in User table
    email_check = await db.execute(select(User).where(User.email == candidate.email))
    if email_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El correo del candidato ya está registrado en la plantilla.")

    # Create active Employee (User)
    new_user = User(
        id=uuid.uuid4().hex,
        email=candidate.email,
        full_name=f"{candidate.first_name} {candidate.last_name}",
        role=payload.role,
        is_active=True,
        hashed_password=hash_password(payload.password),
        phone_number=payload.phone_number or candidate.phone,
        address=payload.address,
        contract_type=payload.contract_type,
        hire_date=payload.hire_date or datetime.now(),
        base_salary=payload.base_salary,
        social_security_number=payload.social_security_number,
        iban=payload.iban,
        country=payload.country or "ES",
        vacation_allowance=30
    )
    db.add(new_user)
    
    # Mark candidate as hired
    candidate.stage = "hired"
    
    # Welcome Notification
    welcome_notif = Notification(
        id=uuid.uuid4().hex,
        user_id=new_user.id,
        title="¡Te damos la bienvenida a la empresa!",
        message=f"Tus credenciales de acceso han sido creadas. Tu contraseña inicial es: {payload.password}",
        type="system",
        is_read=False
    )
    db.add(welcome_notif)

    onboarding_results = {}
    
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error promoting candidate: {str(e)}")

    employee_id = new_user.id

    try:
        from app.services.broadcast import broadcast_notification
        await broadcast_notification(
            db,
            title=f"Candidate Hired: {candidate.first_name} {candidate.last_name}",
            message=f"{candidate.first_name} {candidate.last_name} has been promoted to employee ({payload.role})",
            type_="system",
            role="hr_admin",
            link="/dashboard/hire?tab=candidates",
        )
    except Exception:
        pass

    if payload.assign_onboarding_plan:
        try:
            from app.services.onboarding_planner import generate_onboarding_plan, assign_onboarding_buddy, create_onboarding_workflow
            plan = await generate_onboarding_plan(employee_id, db)
            buddy = await assign_onboarding_buddy(employee_id, db)
            workflow = await create_onboarding_workflow(employee_id, plan, db)
            onboarding_results["plan"] = {"status": "generated", "weeks": plan.get("total_duration_weeks", 0)}
            onboarding_results["buddy"] = buddy.get("selected_buddy", {}).get("full_name", "N/A") if buddy.get("selected_buddy") else "N/A"
            onboarding_results["workflow"] = {"id": workflow.get("workflow_id"), "steps": workflow.get("total_steps", 0)}
        except Exception as e:
            onboarding_results["plan"] = {"status": "failed", "error": str(e)}

    if payload.enroll_in_training:
        try:
            from app.models.training import Course, CourseEnrollment
            courses_result = await db.execute(select(Course).limit(20))
            courses = courses_result.scalars().all()
            enrolled = 0
            for course in courses:
                enrollment = CourseEnrollment(
                    id=uuid.uuid4().hex,
                    user_id=employee_id,
                    course_id=course.id,
                    status="enrolled",
                )
                db.add(enrollment)
                enrolled += 1
            await db.commit()
            onboarding_results["training"] = {"status": "enrolled", "courses": enrolled}
        except Exception as e:
            onboarding_results["training"] = {"status": "failed", "error": str(e)}

    if payload.request_it_equipment:
        try:
            from app.models.it import ITRequisition
            equipment_type = payload.it_equipment_type or "laptop"
            quantity = max(1, payload.it_equipment_quantity)
            for _ in range(quantity):
                requisition = ITRequisition(
                    id=uuid.uuid4().hex,
                    user_id=employee_id,
                    item_type="hardware",
                    item_name=equipment_type.capitalize(),
                    reason=f"New hire onboarding — {candidate.first_name} {candidate.last_name}",
                    status="pending",
                )
                db.add(requisition)
            await db.commit()
            onboarding_results["it_equipment"] = {"status": "requested", "item": equipment_type, "quantity": quantity}
        except Exception as e:
            onboarding_results["it_equipment"] = {"status": "failed", "error": str(e)}
        
    return {
        "message": "Candidato promocionado con éxito. Credenciales creadas y correo de bienvenida enviado.",
        "employee_id": employee_id,
        "onboarding": onboarding_results,
    }

# ---------------------------------------------------------
# AI-Powered Resume Screening Endpoints (F1)
# ---------------------------------------------------------
@router.post("/candidates/screen")
@limiter.limit("20/minute")
async def screen_candidate_full(
    request: Request,
    file: UploadFile = File(...),
    job_id: str = Form(...),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter", "manager"]))
):
    """Upload a resume file and get a comprehensive AI screening report including scores, bias detection, and interview questions."""
    tenant_id = _get_tenant_id(request)
    _check_rate_limit(tenant_id, _screen_bucket, _screen_rate, _screen_burst)

    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
    MAX_SIZE = 10 * 1024 * 1024
    filename = file.filename or "resume"
    ext = os.path.splitext(filename)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: '{ext}'. Accepted: .pdf, .docx, .txt")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum 10 MB.")

    job_res = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    if not job_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Job posting not found")

    from app.services.candidate_screener import screen_resume_full
    try:
        result = await screen_resume_full(content, filename, job_id=job_id, db=db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screening failed: {str(e)}")

    return result


@router.post("/candidates/rank")
async def rank_candidates_endpoint(
    payload: CandidateRankRequest,
    request: Request = None,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter", "manager"]))
):
    """Rank multiple candidates against a job posting using AI scoring with sub-scores and recommendations."""
    tenant_id = _get_tenant_id(request)
    _check_rate_limit(tenant_id, _rank_bucket, _rank_rate, _rank_burst)

    if not payload.candidate_ids:
        raise HTTPException(status_code=400, detail="candidate_ids must not be empty")
    if len(payload.candidate_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 candidates per ranking request")

    job_res = await db.execute(select(JobPosting).where(JobPosting.id == payload.job_id))
    if not job_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Job posting not found")

    from app.services.candidate_screener import rank_candidates
    try:
        result = await rank_candidates(payload.candidate_ids, payload.job_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ranking failed: {str(e)}")

    if isinstance(result, list) and len(result) > 0 and "error" in result[0]:
        raise HTTPException(status_code=400, detail=result[0]["error"])

    return {"job_id": payload.job_id, "ranked_candidates": result, "total": len(result)}


@router.post("/candidates/{candidate_id}/interview-questions")
async def generate_interview_questions_endpoint(
    candidate_id: str,
    job_id: str = Form(...),
    request: Request = None,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter", "manager"]))
):
    """Generate 5-8 tailored interview questions for a candidate based on their profile vs job requirements."""
    tenant_id = _get_tenant_id(request)
    _check_rate_limit(tenant_id, _questions_bucket, _questions_rate, _questions_burst)

    candidate_res = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = candidate_res.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    job_res = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")

    job_requirements = f"Title: {job.title}\n"
    if job.department:
        job_requirements += f"Department: {job.department}\n"
    if job.location:
        job_requirements += f"Location: {job.location}\n"
    if job.description:
        job_requirements += f"Description: {job.description}\n"

    candidate_profile = {
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "email": candidate.email,
        "phone": candidate.phone,
        "notes": candidate.notes,
        "stage": candidate.stage,
    }

    from app.services.candidate_screener import generate_interview_questions
    try:
        questions = await generate_interview_questions(candidate_profile, job_requirements)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Question generation failed: {str(e)}")

    question_count = len(questions) if isinstance(questions, list) else 0
    return {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "job_title": job.title,
        "question_count": question_count,
        "questions": questions,
    }


@router.post("/candidates/batch-screen")
@limiter.limit("20/minute")
async def batch_screen_endpoint(
    request: Request,
    files: List[UploadFile] = File(...),
    job_id: str = Form(...),
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter", "manager"]))
):
    """Batch screen multiple resume files concurrently and return them ranked by AI score."""
    tenant_id = _get_tenant_id(request)
    _check_rate_limit(tenant_id, _screen_bucket, _screen_rate, _screen_burst)
    
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
        
    job_res = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    if not job_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Job posting not found")
        
    files_to_screen = []
    for file in files:
        content = await file.read()
        files_to_screen.append({
            "filename": file.filename or "resume",
            "content": content
        })
        
    from app.services.candidate_screener import batch_screen_resumes
    try:
        ranked_reports = await batch_screen_resumes(files_to_screen, job_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch screening failed: {str(e)}")
        
    return {"job_id": job_id, "ranked_reports": ranked_reports, "total": len(ranked_reports)}


@router.post("/candidates/{candidate_id}/offer-letter")
async def generate_offer_letter_endpoint(
    candidate_id: str,
    payload: OfferLetterRequest,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter"]))
):
    """Generates a personalized offer letter using LLM based on candidate profile and template."""
    from app.services.candidate_screener import generate_personalized_offer_letter
    result = await generate_personalized_offer_letter(
        candidate_id=candidate_id,
        job_id=payload.job_id,
        salary=payload.salary,
        start_date=payload.start_date,
        template=payload.template,
        db=db
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/interviews/video-analysis")
async def analyze_video(
    body: dict,
    db: AsyncSession = Depends(get_tenant_db),
    _: dict = Depends(require_roles(["hr_admin", "recruiter", "manager"]))
):
    """
    Mock endpoint to analyze a video interview recording.
    Expects 'candidate_id' and 'video_url' in the body.
    """
    candidate_id = body.get("candidate_id")
    video_url = body.get("video_url")
    
    if not candidate_id or not video_url:
        raise HTTPException(status_code=400, detail="candidate_id and video_url are required")
        
    from app.services.video_analysis import analyze_video_interview, VideoAnalysisRequest
    req = VideoAnalysisRequest(candidate_id=candidate_id, video_url=video_url)
    result = await analyze_video_interview(req)
    
    return result

# ---------------------------------------------------------
# Public Job Board Endpoints (no auth required)
# ---------------------------------------------------------
@public_router.get("/public/jobs")
async def get_public_jobs(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(
        select(JobPosting).where(JobPosting.status == "open").order_by(JobPosting.created_at.desc())
    )
    jobs = result.scalars().all()
    return [{
        "id": j.id,
        "title": j.title,
        "department": j.department,
        "location": j.location,
        "employment_type": j.employment_type,
        "description": j.description[:500] if j.description else None,
        "posted_at": j.created_at.isoformat() if j.created_at else None,
    } for j in jobs]

@public_router.get("/public/jobs/{job_id}")
async def get_public_job_detail(job_id: str, db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id, JobPosting.status == "open"))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id, "title": job.title, "department": job.department,
        "location": job.location, "employment_type": job.employment_type,
        "description": job.description, "posted_at": job.created_at.isoformat() if job.created_at else None,
    }

@public_router.post("/public/apply")
async def public_apply_for_job(payload: PublicApplicationRequest, db: AsyncSession = Depends(get_tenant_db)):
    job_res = await db.execute(select(JobPosting).where(JobPosting.id == payload.job_id, JobPosting.status == "open"))
    if not job_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Job not found or no longer accepting applications")

    candidate = Candidate(
        id=uuid.uuid4().hex,
        job_id=payload.job_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone or "",
        resume_url=payload.resume_url or "",
        stage="applied",
        source="public_careers",
        notes=payload.cover_letter or "",
    )
    db.add(candidate)
    await db.commit()
    return {"success": True, "message": "Application submitted successfully"}

@public_router.get("/public/jobs/feed.xml")
async def get_jobs_xml_feed(db: AsyncSession = Depends(get_tenant_db)):
    result = await db.execute(
        select(JobPosting).where(JobPosting.status == "open").order_by(JobPosting.created_at.desc())
    )
    jobs = result.scalars().all()

    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<source>', '<publisher>SuccessCore</publisher>', '<publisherurl>https://successcore.com</publisherurl>']
    for job in jobs:
        xml_parts.append(f'''<job>
    <title><![CDATA[{job.title}]]></title>
    <date><![CDATA[{job.created_at.isoformat() if job.created_at else ''}]]></date>
    <referencenumber><![CDATA[{job.id}]]></referencenumber>
    <url><![CDATA[https://successcore.com/careers/{job.id}]]></url>
    <company><![CDATA[SuccessCore]]></company>
    <city><![CDATA[{job.location or ''}]]></city>
    <state><![CDATA[]]></state>
    <country><![CDATA[ES]]></country>
    <description><![CDATA[{job.description or ''}]]></description>
    <department><![CDATA[{job.department or ''}]]></department>
    <jobtype><![CDATA[{job.employment_type or 'full-time'}]]></jobtype>
</job>''')
    xml_parts.append('</source>')

    return Response(content="\n".join(xml_parts), media_type="application/xml")
